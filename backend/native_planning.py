"""Native work planner: real-contact evidence, scoped tasks and durable reminders. OFF."""
import os,json,uuid,hashlib,calendar
from datetime import datetime,date,time,timedelta,timezone
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,field_validator,model_validator
from sqlalchemy import select
from backend.db import Session,Salon,User,Activity,Appointment,now
from backend.security import current,manager,database
from backend.native_models import ContactPolicy,WorkSettings,Task,Notification
from backend.contact_guard import lock_contact
from backend.meta_models import MetaConversation

router=APIRouter(prefix='/api/focus-calendar',tags=['Natywny kalendarz'])
ZONE=ZoneInfo('Europe/Warsaw')
DEFAULTS={'A+':7,'A':14,'B':30,'C':60}
CONTACT_KINDS=('call','visit','email_received','instagram_received')
def schema_enabled():return os.getenv('FOCUS_CALENDAR_SCHEMA_ENABLED','false').strip().lower()=='true'
def enabled():return schema_enabled() and os.getenv('FOCUS_CALENDAR_ENABLED','false').strip().lower()=='true'
def require():
    if not enabled():raise HTTPException(404,'Kalendarz Focus wyłączony')
def stamp(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        if d.tzinfo is None:raise ValueError()
        return d.astimezone(timezone.utc)
    except (ValueError,TypeError):raise HTTPException(422,'Wymagana poprawna data ze strefą') from None
def local_stamp(value,fold=None):
    try:
        local=datetime.fromisoformat(value)
        if local.tzinfo is not None:raise ValueError()
    except (ValueError,TypeError):raise HTTPException(422,'Podaj lokalny termin Warszawy') from None
    candidates={}
    for n in (0,1):
        zoned=local.replace(tzinfo=ZONE,fold=n);utc=zoned.astimezone(timezone.utc)
        if utc.astimezone(ZONE).replace(tzinfo=None)==local:candidates[n]=utc
    if not candidates:raise HTTPException(422,'Ta godzina nie istnieje podczas zmiany czasu')
    if len(set(candidates.values()))>1 and fold is None:raise HTTPException(422,'Wybierz pierwsze lub drugie wystąpienie godziny')
    return candidates.get(fold if fold is not None else 0,next(iter(candidates.values()))).isoformat()

def today():return datetime.now(ZONE).date()
def day_value(value):
    try:return date.fromisoformat(value) if value else today()
    except ValueError:raise HTTPException(422,'Nieprawidłowa data') from None
def access(db,id,user):
    salon=db.get(Salon,id,populate_existing=True,with_for_update={'key_share':True})
    if not salon or (user.role!='manager' and salon.owner_id!=user.id):raise HTTPException(404,'Brak salonu')
    return salon
def blocked(db,s):return s.status=='do_not_contact' or bool(db.scalar(select(MetaConversation.id).where(MetaConversation.salon_id==s.id,MetaConversation.opted_out==1).limit(1)))
def audit(db,salon,user,body):db.add(Activity(id=str(uuid.uuid4()),salon_id=salon.id,user_id=user.id,kind='focus_task',body=body))
def settings(db,user_id):
    row=db.get(WorkSettings,user_id)
    return json.loads(row.intervals) if row else DEFAULTS.copy()
def list_due(db,user,day,representative_id='',salon_id=''):
    if representative_id and user.role!='manager' and representative_id!=user.id:raise HTTPException(403,'Niedozwolony handlowiec')
    query=select(Salon).join(User,User.id==Salon.owner_id).where(User.active==1)
    if user.role!='manager':query=query.where(Salon.owner_id==user.id)
    if representative_id:query=query.where(Salon.owner_id==representative_id)
    if salon_id:query=query.where(Salon.id==salon_id)
    result=[]
    for s in db.scalars(query):
        if blocked(db,s):continue
        # Only explicitly registered contact evidence counts, never scheduling/drafts/tasks.
        contacts=[]
        for a in db.scalars(select(Activity).where(Activity.salon_id==s.id,Activity.kind.in_(CONTACT_KINDS))):
            try:at=stamp(a.created_at)
            except HTTPException:continue
            if at<=datetime.now(timezone.utc) and at.astimezone(ZONE).date()<=day:contacts.append((at,a.id))
        last=max(contacts,default=None)
        base=last[0].astimezone(ZONE).date() if last else stamp(s.created_at).astimezone(ZONE).date()
        elapsed=max(0,(day-base).days)
        policy=db.get(ContactPolicy,s.id);interval=policy.interval_days if policy else settings(db,s.owner_id).get(s.priority,30)
        due=base+timedelta(days=interval)
        # Never-contacted leads appear immediately; age is explicitly since registration.
        cycle=last[1] if last else 'never'
        task=db.scalar(select(Task).where(Task.salon_id==s.id,Task.cycle_key.like('followup:%'),Task.status.in_(('planned','in_progress'))))
        result.append({'salon_id':s.id,'salon_name':s.name,'owner_id':s.owner_id,'priority':s.priority,'last_contact_at':last[0].isoformat() if last else None,'days_since_contact':elapsed if last else None,'days_since_registration':max(0,(day-stamp(s.created_at).astimezone(ZONE).date()).days),'threshold':max([v for v in (7,14,30,60) if elapsed>=v],default=0),'interval_days':interval,'due_on':due.isoformat() if last else day.isoformat(),'requires_contact':not last or day>=due,'overdue_days':max(0,(day-due).days) if last else elapsed,'cycle':cycle,'task_id':task.id if task else None})
    return sorted(result,key=lambda r:({'A+':0,'A':1,'B':2,'C':3}.get(r['priority'],4),-r['overdue_days'],r['salon_name']))

def ensure_followups(db,user,day):
    made=0
    for candidate in list_due(db,user,day):
        lock_contact(db,candidate['salon_id']);s=access(db,candidate['salon_id'],user)
        # Re-evaluate contact/opt-out under the same lock used by the recorder.
        row=next((r for r in list_due(db,user,day,s.owner_id,s.id) if r['salon_id']==s.id),None)
        if not row:continue
        key='followup:'+s.id+':'+row['cycle']
        existing=db.scalar(select(Task).where(Task.salon_id==s.id,Task.cycle_key.like('followup:%'),Task.status.in_(('planned','in_progress'))).with_for_update())
        if existing and existing.cycle_key!=key:
            existing.status='cancelled';existing.result='Zastąpiono po zarejestrowaniu nowego kontaktu.';existing.version+=1;existing=None
        if existing:
            if existing.assignee_id!=s.owner_id:existing.assignee_id=s.owner_id;existing.version+=1
            continue
        if not row['requires_contact']:continue
        if db.scalar(select(Task.id).where(Task.cycle_key==key)):continue
        task=Task(id=str(uuid.uuid4()),salon_id=s.id,assignee_id=s.owner_id,title='Ponowny kontakt: '+s.name[:150],due_at=datetime.combine(day,time(9),ZONE).astimezone(timezone.utc).isoformat(),priority='urgent' if s.priority=='A+' else 'high' if s.priority=='A' else 'normal',cycle_key=key)
        db.add(task);audit(db,s,user,'Przygotowano zadanie ponownego kontaktu. Nie odnotowano kontaktu.');made+=1
        db.flush()
    return made

@router.get('/status')
def status(user=Depends(current)):return {'enabled':enabled(),'schema_enabled':schema_enabled(),'external_messages':False,'push':'not_configured'}
@router.get('/contacts')
def contacts(day:str='',representative_id:str='',user=Depends(current),db=Depends(database)):
    require();return list_due(db,user,day_value(day),representative_id)
class PolicyIn(BaseModel):interval_days:int=Field(ge=1,le=365)
@router.put('/contacts/{id}/policy')
def policy(id:str,body:PolicyIn,user=Depends(current),db=Depends(database)):
    require();lock_contact(db,id);s=access(db,id,user);row=db.get(ContactPolicy,id)
    if not row:row=ContactPolicy(salon_id=id,interval_days=body.interval_days);db.add(row)
    else:row.interval_days=body.interval_days
    audit(db,s,user,'Zmieniono okres kontaktu na '+str(body.interval_days)+' dni.');db.commit();return {'interval_days':row.interval_days}
class SettingsIn(BaseModel):
    intervals:dict[str,int]
    reminders:list[int]=Field(default=[1440,120,30],max_length=5)
    @field_validator('intervals')
    @classmethod
    def valid_intervals(cls,v):
        if set(v)!=set(DEFAULTS) or any(isinstance(n,bool) or not 1<=n<=365 for n in v.values()):raise ValueError('Wymagane A+/A/B/C i okresy1–365')
        return v
    @field_validator('reminders')
    @classmethod
    def valid_reminders(cls,v):
        if any(n<0 or n>10080 for n in v) or len(v)!=len(set(v)):raise ValueError('Minuty0–10080, bez duplikatów')
        return v
@router.get('/settings')
def get_settings(user=Depends(current),db=Depends(database)):
    require();row=db.get(WorkSettings,user.id)
    return {'intervals':settings(db,user.id),'reminders':json.loads(row.reminders) if row else [1440,120,30]}

@router.put('/settings/{user_id}')
def save_settings(user_id:str,body:SettingsIn,user=Depends(current),db=Depends(database)):
    require()
    if user.role!='manager' and user_id!=user.id:raise HTTPException(403,'Niedozwolone ustawienia')
    target=db.get(User,user_id)
    if not target or not target.active:raise HTTPException(404,'Brak użytkownika')
    target=db.get(User,user_id,with_for_update=True);row=db.get(WorkSettings,user_id)
    if not row:row=WorkSettings(user_id=user_id);db.add(row)
    row.intervals=json.dumps(body.intervals);row.reminders=json.dumps(body.reminders);db.commit();return {'ok':True}
@router.post('/prepare')
def prepare(user=Depends(current),db=Depends(database)):
    require();made=ensure_followups(db,user,today());db.commit();return {'created':made,'contact_recorded':False}
class TaskIn(BaseModel):
    salon_id:str
    title:str=Field(min_length=1,max_length=180)
    due_at:str|None=None
    local_due:str|None=None
    fold:Literal[0,1]|None=None
    priority:Literal['low','normal','high','urgent']='normal'
    repeat_days:int=Field(default=0,ge=0,le=365)
    assignee_id:str=''
    @model_validator(mode='after')
    def one_time(self):
        if bool(self.due_at)==bool(self.local_due):raise ValueError('Podaj dokładnie jeden termin')
        return self
class TaskEdit(BaseModel):
    version:int
    status:Literal['planned','in_progress','completed','cancelled']='planned'
    due_at:str|None=None
    local_due:str|None=None
    fold:Literal[0,1]|None=None
    result:str=Field(default='',max_length=4000)
    contact_kind:Literal['call','visit','email_received']|None=None

def task_view(t):
    return {k:getattr(t,k) for k in ('id','salon_id','assignee_id','title','due_at','priority','status','repeat_days','result','version','completed_at')}|{'overdue':t.status in ('planned','in_progress') and stamp(t.due_at)<datetime.now(timezone.utc)}
@router.post('/tasks',status_code=201)
def create_task(body:TaskIn,user=Depends(current),db=Depends(database)):
    require();lock_contact(db,body.salon_id);s=access(db,body.salon_id,user)
    if blocked(db,s):raise HTTPException(409,'Kontakt zablokowany')
    assignee=body.assignee_id or s.owner_id
    if assignee!=s.owner_id:raise HTTPException(409,'Zadanie musi należeć do opiekuna salonu')
    due=local_stamp(body.local_due,body.fold) if body.local_due else stamp(body.due_at).isoformat()
    duplicate=db.scalar(select(Task.id).where(Task.salon_id==s.id,Task.title==body.title,Task.due_at==due,Task.status.in_(('planned','in_progress'))))
    if duplicate:raise HTTPException(409,'Takie zadanie już istnieje')
    row=Task(id=str(uuid.uuid4()),salon_id=s.id,assignee_id=assignee,title=body.title,due_at=due,priority=body.priority,repeat_days=body.repeat_days)
    db.add(row);audit(db,s,user,'Utworzono zadanie: '+body.title);db.commit();return task_view(row)
@router.patch('/tasks/{id}')
def edit_task(id:str,body:TaskEdit,user=Depends(current),db=Depends(database)):
    require();row=db.get(Task,id)
    if not row:raise HTTPException(404,'Brak zadania')
    lock_contact(db,row.salon_id);s=access(db,row.salon_id,user)
    row=db.get(Task,id,populate_existing=True,with_for_update=True)
    if row.version!=body.version:raise HTTPException(409,'Zadanie zmienione, odśwież')
    if row.status in ('completed','cancelled'):raise HTTPException(409,'Zadanie już zamknięte')
    if body.status=='completed' and not body.result.strip():raise HTTPException(422,'Zapisz wynik działania')
    if body.contact_kind and (body.status!='completed' or blocked(db,s)):raise HTTPException(409,'Nie można zarejestrować kontaktu')
    before={k:getattr(row,k) for k in ('due_at','status','assignee_id','version')}
    if body.due_at and body.local_due:raise HTTPException(422,'Podaj jeden termin')
    if body.local_due:row.due_at=local_stamp(body.local_due,body.fold)
    elif body.due_at:row.due_at=stamp(body.due_at).isoformat()
    row.assignee_id=s.owner_id;row.status=body.status;row.result=body.result;row.version+=1
    audit(db,s,user,'Zmieniono zadanie '+row.id+': '+json.dumps({'before':before,'after':{k:getattr(row,k) for k in ('due_at','status','assignee_id','version')}},ensure_ascii=False)+'. Wynik: '+body.result)
    if body.status=='completed':
        row.completed_at=now()
        if body.contact_kind:db.add(Activity(id=str(uuid.uuid4()),salon_id=s.id,user_id=user.id,kind=body.contact_kind,body=body.result))
        if row.repeat_days and not blocked(db,s):
            # Next occurrence uses local wall time, preserving Warsaw DST transitions.
            due=(stamp(row.due_at).astimezone(ZONE)+timedelta(days=row.repeat_days)).astimezone(timezone.utc).isoformat()
            db.add(Task(id=str(uuid.uuid4()),salon_id=s.id,assignee_id=s.owner_id,title=row.title,due_at=due,priority=row.priority,repeat_days=row.repeat_days,cycle_key='repeat:'+row.id))
    db.commit();return task_view(row)
@router.get('/tasks')
def tasks(user=Depends(current),db=Depends(database)):
    require();query=select(Task).join(Salon,Salon.id==Task.salon_id)
    if user.role!='manager':query=query.where(Salon.owner_id==user.id)
    return [task_view(t) for t in db.scalars(query.order_by(Task.due_at).limit(1000))]
@router.get('/report')
def report(day:str='',representative_id:str='',user=Depends(current),db=Depends(database)):
    require();d=day_value(day);rows=list_due(db,user,d,representative_id);due=[r for r in rows if r['requires_contact']]
    task_rows=tasks(user,db)
    owners={s.id:s.owner_id for s in db.scalars(select(Salon).where(Salon.id.in_([t['salon_id'] for t in task_rows])))}
    if representative_id:task_rows=[t for t in task_rows if owners.get(t['salon_id'])==representative_id]
    start=datetime.combine(d,time.min,ZONE).astimezone(timezone.utc)
    end=datetime.combine(d+timedelta(days=1),time.min,ZONE).astimezone(timezone.utc)
    instant=datetime.now(timezone.utc)
    query=select(Appointment,Salon).join(Salon,Salon.id==Appointment.salon_id).where(Appointment.user_id==Salon.owner_id,Appointment.starts_at>=start.isoformat(),Appointment.starts_at<end.isoformat())
    if user.role!='manager':query=query.where(Appointment.user_id==user.id)
    if representative_id:query=query.where(Appointment.user_id==representative_id)
    visits=[{'id':a.id,'salon_id':a.salon_id,'salon_name':s.name,'representative_id':a.user_id,'starts_at':a.starts_at,'ends_at':a.ends_at,'status':a.status} for a,s in db.execute(query.order_by(Appointment.starts_at))]
    salon_ids=[r['salon_id'] for r in rows]
    contacts=list(db.scalars(select(Activity).where(Activity.salon_id.in_(salon_ids),Activity.kind.in_(CONTACT_KINDS),Activity.created_at>=start.isoformat(),Activity.created_at<end.isoformat(),Activity.created_at<=instant.isoformat())))
    groups=[]
    if user.role=='manager':
        for u in db.scalars(select(User).where(User.active==1)):
            if representative_id and u.id!=representative_id:continue
            subset=[r for r in due if r['owner_id']==u.id];owned=[t for t in task_rows if owners.get(t['salon_id'])==u.id]
            groups.append({'representative_id':u.id,'name':u.name,'neglected':len(subset),'high_priority':sum(r['priority'] in ('A+','A') for r in subset),'overdue_tasks':sum(t['overdue'] for t in owned),'completed_tasks':sum(t['status']=='completed' for t in owned),'completed_on_time':sum(t['status']=='completed' and stamp(t['completed_at'])<=stamp(t['due_at']) for t in owned),'contacts_recorded':sum(a.user_id==u.id for a in contacts),'visits_completed_recorded':sum(v['representative_id']==u.id and v['status']=='completed' for v in visits),'visits_uncompleted':sum(v['representative_id']==u.id and v['status'] in ('proposed','confirmed') and stamp(v['ends_at'])<instant for v in visits)})
    upcoming_tasks=[t for t in task_rows if t['status'] in ('planned','in_progress') and instant<=stamp(t['due_at'])<=instant+timedelta(hours=24)]
    return {'day':d.isoformat(),'generated_at':instant.isoformat(),'time_zone':'Europe/Warsaw','requires_contact':due,'all_contacts':rows,'team':groups,'tasks':task_rows,'tasks_today':[t for t in task_rows if stamp(t['due_at']).astimezone(ZONE).date()==d],'overdue_tasks':[t for t in task_rows if t['overdue']],'due_next_24h':upcoming_tasks,'visits_today':visits,'visits_next_2h':[v for v in visits if v['status']=='confirmed' and instant<=stamp(v['starts_at'])<=instant+timedelta(hours=2)],'at_risk_tasks':[t for t in upcoming_tasks if t['status']=='planned' and stamp(t['due_at'])<=instant+timedelta(hours=2)],'rules':'Tylko zarejestrowane kontakty. Ryzyko: zadanie nierozpoczęte z terminem do2h. Niewykonana wizyta: koniec minął, nadal proposed/confirmed; to brak rejestracji, nie dowód nieobecności.'}


def reminders(db):
    for t in db.scalars(select(Task).where(Task.status.in_(('planned','in_progress'))).order_by(Task.due_at).limit(500)):
        s=db.get(Salon,t.salon_id)
        if blocked(db,s):continue
        key='task:'+t.id+':'+str(t.version)
        if stamp(t.due_at)<=datetime.now(timezone.utc):
            notification=db.get(Notification,key)
            if not notification:db.add(Notification(key=key,user_id=s.owner_id,task_id=t.id,at=now()))
            elif notification.user_id!=s.owner_id:notification.user_id=s.owner_id;notification.read=0
    for a in db.scalars(select(Appointment).where(Appointment.status=='confirmed')):
        s=db.get(Salon,a.salon_id)
        if s.owner_id!=a.user_id or blocked(db,s):continue
        config=db.get(WorkSettings,a.user_id);minutes=json.loads(config.reminders) if config else [1440,120,30]
        delta=(stamp(a.starts_at)-datetime.now(timezone.utc)).total_seconds()/60
        eligible=[m for m in minutes if 0<=delta<=m]
        for offset in ([min(eligible)] if eligible else []):
            key='visit:'+a.id+':'+hashlib.sha256(a.starts_at.encode()).hexdigest()[:16]+':'+str(offset)
            if 0<=delta<=offset and not db.get(Notification,key):db.add(Notification(key=key,user_id=a.user_id,appointment_id=a.id,at=now()))
@router.get('/notifications')
def notifications(user=Depends(current),db=Depends(database)):
    require();result=[]
    for n in db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(Notification.at.desc()).limit(100)):
        t=db.get(Task,n.task_id) if n.task_id else None;a=db.get(Appointment,n.appointment_id) if n.appointment_id else None
        s=db.get(Salon,t.salon_id if t else a.salon_id) if t or a else None
        if not s or s.owner_id!=user.id or blocked(db,s):continue
        if t and (t.status not in ('planned','in_progress') or n.key!='task:'+t.id+':'+str(t.version)):continue
        if a:
            config=db.get(WorkSettings,a.user_id);minutes=json.loads(config.reminders) if config else [1440,120,30]
            delta=(stamp(a.starts_at)-datetime.now(timezone.utc)).total_seconds()/60
            eligible=[m for m in minutes if 0<=delta<=m]
            if a.status!='confirmed' or hashlib.sha256(a.starts_at.encode()).hexdigest()[:16] not in n.key or not eligible or n.key.rsplit(':',1)[-1]!=str(min(eligible)):continue
        result.append({'key':n.key,'title':t.title if t else 'Zbliża się wizyta: '+s.name,'at':n.at,'read':bool(n.read)})
    return result
@router.post('/notifications/{key}/read')
def read_notification(key:str,user=Depends(current),db=Depends(database)):
    require();n=db.get(Notification,key)
    if not n or n.user_id!=user.id:raise HTTPException(404,'Brak powiadomienia')
    n.read=1;db.commit();return {'ok':True}

def tick():
    if not enabled():return False
    with Session() as db:
        # One existing worker; advisory lock also prevents two instances racing notifications.
        if db.bind.dialect.name=='postgresql':
            from sqlalchemy import text
            if not db.scalar(text("SELECT pg_try_advisory_xact_lock(hashtextextended('focus-native-tick',0))")):return False
        from types import SimpleNamespace
        for u in db.scalars(select(User).where(User.active==1)):ensure_followups(db,SimpleNamespace(id=u.id,role='sales'),today())
        reminders(db);db.commit()
    return True
