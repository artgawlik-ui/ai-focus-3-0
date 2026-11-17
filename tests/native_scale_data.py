"""Synthetic-only scale fixtures; refuses non-local/non-test database targets."""
import hashlib,os
from datetime import datetime,timedelta,timezone
from sqlalchemy import insert
from backend.db import Salon,Activity,Appointment
from backend.native_models import Task

def seed(db,count,owners=('rep1','rep2')):
    url=db.bind.url
    if os.getenv('APP_ENV')!='test' or url.host not in ('localhost','127.0.0.1','postgres') or not str(url.database).startswith(('focus3_native_','focus3_scale_','focus3_ci_')):raise RuntimeError('Synthetic fixture target refused')
    instant=datetime.now(timezone.utc);old=(instant-timedelta(days=100)).isoformat();last=(instant-timedelta(days=61)).isoformat();due=(instant-timedelta(days=1)).isoformat();future=(instant+timedelta(hours=1)).isoformat();end=(instant+timedelta(hours=1,minutes=20)).isoformat()
    for start in range(0,count,500):
        salons=[];tasks=[];visits=[];activities=[]
        for i in range(start,min(count,start+500)):
            id=f'synthetic-salon-{i:06d}';owner=owners[i%len(owners)]
            salons.append({'id':id,'owner_id':owner,'name':f'[SYNTHETIC] Salon {i:06d}','city':'Miasto syntetyczne','priority':('A+','A','B','C')[i%4],'created_at':old,'dedup_key':hashlib.sha256(('synthetic:'+str(i)).encode()).hexdigest()})
            tasks.append({'id':f'synthetic-task-{i:06d}','salon_id':id,'assignee_id':owner,'title':f'[SYNTHETIC] Zadanie {i:06d}','due_at':due,'priority':'normal','status':'planned','created_at':old})
            visits.append({'id':f'synthetic-visit-{i:06d}','salon_id':id,'user_id':owner,'starts_at':future,'ends_at':end,'status':'confirmed'})
            activities.extend([{'id':f'synthetic-call-{i:06d}','salon_id':id,'user_id':owner,'kind':'call','body':'Syntetyczna historia','created_at':last},{'id':f'synthetic-draft-{i:06d}','salon_id':id,'user_id':owner,'kind':'agent_draft','body':'Szkic syntetyczny, bez wysyłki','created_at':instant.isoformat()}])
        db.execute(insert(Salon),salons);db.execute(insert(Task),tasks);db.execute(insert(Appointment),visits);db.execute(insert(Activity),activities)
    db.commit()
