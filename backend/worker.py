"""Separate durable DB queue consumer. Never sends messages or changes a salon priority."""
import json, logging, os, time
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from backend.db import Session, Job, Salon, Activity, User, now
from backend.main import uid
log=logging.getLogger('worker')
_last_meta_monitor=0.0

def authorized_salon(db, job, final=False):
    # Refresh identity-map entries after a slow provider call; lock through final commit.
    if final:
        from backend.contact_guard import lock_contact
        lock_contact(db, job.salon_id)
    options = {'populate_existing': True, 'with_for_update': True} if final else {}
    requester = db.get(User, job.user_id, **options)
    salon = db.get(Salon, job.salon_id, **options)
    if not requester or not requester.active or not salon or (requester.role != 'manager' and salon.owner_id != requester.id):
        raise ValueError('Access revoked')
    from backend.meta_models import MetaConversation
    opted_out = db.scalar(select(MetaConversation.id).where(MetaConversation.salon_id == salon.id, MetaConversation.opted_out == 1).limit(1))
    if salon.status == 'do_not_contact' or opted_out:
        raise ValueError('Kontakt zablokowany')
    return salon

def run_once():
    with Session() as db:
        # Recover interrupted runs; completed job writes and activity are one transaction.
        cutoff=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
        db.execute(update(Job).where(Job.status=='running',Job.updated_at<cutoff).values(status='queued',updated_at=now()))
        db.commit()
        job=db.scalar(select(Job).where(Job.status=='queued').order_by(Job.created_at).with_for_update(skip_locked=True).limit(1))
        if not job: return False
        claim_stamp=now()
        result=db.execute(update(Job).where(Job.id==job.id,Job.status=='queued').values(status='running',updated_at=claim_stamp))
        if result.rowcount!=1: db.rollback(); return False
        db.commit()
        try:
            salon=authorized_salon(db,job)
            history=list(db.scalars(select(Activity).where(Activity.salon_id==salon.id).order_by(Activity.created_at.desc()).limit(15)))
            from backend.meta import agent_replies
            history.extend(agent_replies(db,salon.id))
            recent=any(a.kind in ('call','visit','follow_up') and a.created_at>(datetime.now(timezone.utc)-timedelta(days=7)).isoformat() for a in history)
            from backend.qualification import analyze, minimal_model_context
            analysis=analyze(salon,history,job.evidence)
            # Feature flag permits immediate rollback without changing queue/API schema.
            if os.getenv('AGENT_V2_ENABLED','false').lower()!='true':
                analysis['priority_suggestion']=salon.priority
                analysis['warning']='Tryb podstawowy; punktacja rozszerzona wyłączona. '+analysis['warning']
                analysis.pop('score',None); analysis.pop('criteria',None)
            from backend.agent_provider import add_optional_questions
            add_optional_questions(analysis,minimal_model_context(analysis))
            # Fence a previous executor after recovery/reclaim. Lock and result commit are atomic.
            owned=db.scalar(select(Job).where(Job.id==job.id,Job.status=='running',Job.updated_at==claim_stamp).with_for_update().execution_options(populate_existing=True))
            if not owned:
                db.rollback()
                return True
            salon=authorized_salon(db,job,final=True)
            job.status='completed'; job.result=json.dumps(analysis,ensure_ascii=False); job.updated_at=now()
            db.add(Activity(id=uid(),salon_id=salon.id,user_id=job.user_id,kind='agent_draft',body='Przygotowano analizę i szkic. Nie wysłano wiadomości.'))
            db.commit()
            log.info('agent completed job_id=%s user_id=%s rules=%s sent=false',job.id,job.user_id,analysis.get('rules_version','legacy'))
        except Exception:
            job_id=job.id
            db.rollback()
            owned=db.scalar(select(Job).where(Job.id==job_id,Job.status=='running',Job.updated_at==claim_stamp).with_for_update().execution_options(populate_existing=True))
            if owned:
                owned.status='failed'; owned.result=json.dumps({'error':'Analiza nie powiodła się. Sprawdź konfigurację dostawcy i ponów zadanie.'}); owned.updated_at=now(); db.commit()
                log.warning('Job failed; details suppressed')
        return True

def maintain_meta_once():
    # A missing/invalid optional integration must never starve the CRM queue.
    from backend.meta import expire_content,maintain_credentials
    from backend.meta_flags import feature
    from backend.meta_inbox import maintenance
    try:
        with Session() as db:
            # Retention continues even while ingest/OAuth are disabled.
            expire_content(db)
            maintenance(db)
            if feature('oauth'):maintain_credentials(db)
        return True
    except Exception:
        log.warning('Meta maintenance deferred; CRM queue continues; no customer action performed')
        return False

def process_meta_once():
    global _last_meta_monitor
    # Existing process/cycle only. Optional integration cannot starve CRM jobs.
    try:
        from backend.meta_inbox import drain_once,maintenance
        from backend.meta_refresh import maintain
        from backend.meta import require_config
        from backend.meta_flags import feature
        if feature('crm_history'):
            require_config('crm_history');drain_once()
        if time.monotonic()-_last_meta_monitor>=60:
            with Session() as db:maintenance(db)
            _last_meta_monitor=time.monotonic()
        if feature('oauth'):
            require_config('oauth');maintain()
        return True
    except Exception:
        log.warning('Meta cycle deferred; CRM queue continues')
        return False

def process_google_once():
    from backend.google_transport import writable
    if not writable():return False
    try:
        from backend.google_calendar import process_once
        return process_once()
    except Exception:
        log.warning('Google Calendar cycle deferred; no success assumed')
        return False

def main():
    import signal
    import threading
    from backend.worker_control import paused, publish
    stop_event=threading.Event()
    def stop(*_):stop_event.set()
    previous={sig:signal.signal(sig,stop) for sig in (signal.SIGTERM,signal.SIGINT)}
    last_cleanup=-3600
    try:
        while not stop_event.is_set():
            if paused():
                publish('paused')
                stop_event.wait(2)
                continue
            try:
                publish('running')
                if time.monotonic()-last_cleanup>3600:
                    maintain_meta_once()
                    last_cleanup=time.monotonic()
                if stop_event.is_set() or paused():continue
                process_meta_once()
                if stop_event.is_set() or paused():continue
                process_google_once()
                if stop_event.is_set() or paused():continue
                run_once()
                publish('idle')
                stop_event.wait(2)
            except Exception:
                publish('degraded')
                log.warning('Queue unavailable; retrying after database readiness check')
                stop_event.wait(5)
    finally:
        publish('stopped')
        for sig,handler in previous.items():signal.signal(sig,handler)

if __name__=='__main__':main()
