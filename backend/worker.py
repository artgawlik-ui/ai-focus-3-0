"""Separate durable DB queue consumer. Never sends messages or changes a salon priority."""
import json, logging, os, time
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy import select, update
from backend.db import Session, Job, Salon, Activity, User, now
from backend.main import uid
log=logging.getLogger('worker')

def run_once():
    with Session() as db:
        # Recover interrupted runs; completed job writes and activity are one transaction.
        cutoff=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
        db.execute(update(Job).where(Job.status=='running',Job.updated_at<cutoff).values(status='queued',updated_at=now()))
        db.commit()
        job=db.scalar(select(Job).where(Job.status=='queued').order_by(Job.created_at).with_for_update(skip_locked=True).limit(1))
        if not job: return False
        result=db.execute(update(Job).where(Job.id==job.id,Job.status=='queued').values(status='running',updated_at=now()))
        if result.rowcount!=1: db.rollback(); return False
        db.commit()
        try:
            salon=db.get(Salon,job.salon_id)
            requester=db.get(User,job.user_id)
            if not requester or not requester.active or (requester.role!='manager' and salon.owner_id!=requester.id):raise ValueError('Access revoked')
            if salon.status=='do_not_contact': raise ValueError('Kontakt zablokowany')
            history=list(db.scalars(select(Activity).where(Activity.salon_id==salon.id).order_by(Activity.created_at.desc()).limit(15)))
            recent=any(a.kind in ('call','visit','follow_up') and a.created_at>(datetime.now(timezone.utc)-timedelta(days=7)).isoformat() for a in history)
            from backend.qualification import analyze, minimal_model_context
            analysis=analyze(salon,history,job.evidence)
            # Feature flag permits immediate rollback without changing queue/API schema.
            if os.getenv('AGENT_V2_ENABLED','false').lower()!='true':
                analysis['priority_suggestion']=salon.priority
                analysis['warning']='Tryb podstawowy; punktacja rozszerzona wyłączona. '+analysis['warning']
                analysis.pop('score',None); analysis.pop('criteria',None)
            # A configured key alone never activates paid processing.
            if os.getenv('AI_PAID_PROCESSING_APPROVED','false').lower()=='true' and os.getenv('OPENAI_API_KEY'):
                response=httpx.post('https://api.openai.com/v1/chat/completions',headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},json={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'store':False,'max_completion_tokens':300,'messages':[{'role':'system','content':'Zwróć wyłącznie neutralne pytania po polsku. Nie twórz faktów, decyzji ani wiadomości do wysłania.'},{'role':'user','content':json.dumps(minimal_model_context(analysis),ensure_ascii=False)}]},timeout=60)
                response.raise_for_status()
                questions=response.json()['choices'][0]['message']['content']
                if not isinstance(questions,str) or len(questions)>5000:raise ValueError('Invalid provider result')
                analysis['model_questions_unverified']=questions
                analysis['engine']='rules+openai_questions'
            job.status='completed'; job.result=json.dumps(analysis,ensure_ascii=False); job.updated_at=now()
            db.add(Activity(id=uid(),salon_id=salon.id,user_id=job.user_id,kind='agent_draft',body='Przygotowano analizę i szkic. Nie wysłano wiadomości.'))
            db.commit()
            log.info('agent completed job_id=%s user_id=%s rules=%s sent=false',job.id,job.user_id,analysis.get('rules_version','legacy'))
        except Exception:
            db.rollback(); job=db.get(Job,job.id); job.status='failed'; job.result=json.dumps({'error':'Analiza nie powiodła się. Sprawdź konfigurację dostawcy i ponów zadanie.'}); job.updated_at=now(); db.commit(); log.warning('Job failed id=%s',job.id)
        return True

if __name__=='__main__':
    import signal
    running=True
    def stop(*_):
        global running
        running=False
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    while running:
        try:
            if not run_once(): time.sleep(2)
        except Exception:
            log.warning('Queue unavailable; retrying after database readiness check')
            time.sleep(5)
