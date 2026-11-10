"""Native work planner: real-contact evidence, scoped tasks and durable reminders. OFF."""
import os,json,uuid,hashlib,calendar
from datetime import datetime,date,time,timedelta,timezone
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Response
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
CONTACT_KINDS=('call','visit','email_received','instagram_received','instagram_manual','instagram_reply_manual')
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

def recurring_due(value,days):
    # Preserve the wall clock, skipping a nonexistent occurrence rather than drifting.
    wall=stamp(value).astimezone(ZONE).replace(tzinfo=None)
    for _ in range(3):
        try:wall+=timedelta(days=days)
        except OverflowError:raise HTTPException(422,'Koniec obsługiwanego zakresu cyklu') from None
        candidate=wall.replace(tzinfo=ZONE,fold=0).astimezone(timezone.utc)
        if candidate.astimezone(ZONE).replace(tzinfo=None)==wall:return candidate.isoformat()
    raise HTTPException(422,'Nie można wyznaczyć następnego terminu')

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
    # Compatibility list is bounded. Worker and UI use their own bounded queries.
    from backend.native_queries import contacts_page
    return contacts_page(db,user,day,representative_id,limit=100,salon=salon_id)['items']

def ensure_followups(db,user,day):
    made=0
    from backend.native_queries import contact_work
    for candidate in contact_work(db,user,day):
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
def status(user=Depends(current)):
    from backend.native_diagnostics import diagnostics_enabled
    return {'enabled':enabled(),'schema_enabled':schema_enabled(),'diagnostics_enabled':diagnostics_enabled(),'external_messages':False,'push':'not_configured'}
@router.get('/contacts')
def contacts(response:Response,day:str='',representative_id:str='',limit:int=100,offset:int=0,user=Depends(current),db=Depends(database)):
    require()
    from backend.native_queries import contacts_page
    page=contacts_page(db,user,day_value(day),representative_id,limit,offset)
    response.headers['X-Focus-Total']=str(page['total']);response.headers['X-Focus-Has-More']=str(page['has_more']).lower()
    return page['items']
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
            due=recurring_due(row.due_at,row.repeat_days)
            db.add(Task(id=str(uuid.uuid4()),salon_id=s.id,assignee_id=s.owner_id,title=row.title,due_at=due,priority=row.priority,repeat_days=row.repeat_days,cycle_key='repeat:'+row.id))
    db.commit();return task_view(row)
@router.get('/tasks')
def tasks(response:Response,limit:int=100,offset:int=0,user=Depends(current),db=Depends(database)):
    require()
    from backend.native_queries import tasks_page
    page=tasks_page(db,user,limit=limit,offset=offset)
    response.headers['X-Focus-Total']=str(page['total']);response.headers['X-Focus-Has-More']=str(page['has_more']).lower()
    return page['items']

@router.get('/report')
def report(day:str='',representative_id:str='',user=Depends(current),db=Depends(database)):
    require();d=day_value(day)
    from backend.native_queries import contacts_page,tasks_page,report_summary
    counts,team=report_summary(db,user,d,representative_id)
    cp=contacts_page(db,user,d,representative_id,limit=20,due_only=True)
    all_cp=contacts_page(db,user,d,representative_id,limit=20)
    tp=tasks_page(db,user,representative_id,limit=20)
    vp=visits_page(day=day,days=1,representative_id=representative_id,user=user,db=db)
    instant=datetime.now(timezone.utc)
    return {'day':d.isoformat(),'generated_at':instant.isoformat(),'time_zone':'Europe/Warsaw','counts':counts,'pages':{'contacts':cp['total'],'all_contacts':all_cp['total'],'tasks':tp['total'],'visits':vp['total']},'requires_contact':cp['items'],'all_contacts':all_cp['items'],'team':team,'tasks':tp['items'],'tasks_today':[t for t in tp['items'] if stamp(t['due_at']).astimezone(ZONE).date()==d],'overdue_tasks':[t for t in tp['items'] if t['overdue']],'due_next_24h':[t for t in tp['items'] if t['status'] in ('planned','in_progress') and instant<=stamp(t['due_at'])<=instant+timedelta(hours=24)],'visits_today':vp['items'],'visits_next_2h':[v for v in vp['items'] if v['status']=='confirmed' and instant<=stamp(v['starts_at'])<=instant+timedelta(hours=2)],'at_risk_tasks':[t for t in tp['items'] if t['status']=='planned' and instant<=stamp(t['due_at'])<=instant+timedelta(hours=2)],'rules':'Agregaty counts obejmują cały zakres; listy są podglądem20 rekordów. Ryzyko: nierozpoczęte zadanie do2h. Plan nie jest kontaktem ani dowodem odbycia wizyty.'}


def filters_valid(from_date,to_date,priority,allowed):
    if from_date:day_value(from_date)
    if to_date:day_value(to_date)
    if from_date and to_date and from_date>to_date:raise HTTPException(422,'Odwrócony zakres dat')
    if priority and priority not in allowed:raise HTTPException(422,'Nieprawidłowy priorytet')

@router.get('/contacts/page')
def contacts_paged(day:str='',representative_id:str='',search:str='',priority:str='',due_only:bool=False,from_date:str='',to_date:str='',limit:int=20,offset:int=0,user=Depends(current),db=Depends(database)):
    require();filters_valid(from_date,to_date,priority,DEFAULTS)
    if len(search)>160:raise HTTPException(422,'Za długie wyszukiwanie')
    from backend.native_queries import contacts_page
    return contacts_page(db,user,day_value(day),representative_id,limit,offset,search=search,priority=priority,due_only=due_only,from_date=from_date,to_date=to_date)

@router.get('/tasks/page')
def tasks_paged(representative_id:str='',search:str='',priority:str='',status:str='',from_date:str='',to_date:str='',limit:int=20,offset:int=0,user=Depends(current),db=Depends(database)):
    require();filters_valid(from_date,to_date,priority,('low','normal','high','urgent'))
    if len(search)>160 or status not in ('','planned','in_progress','completed','cancelled'):raise HTTPException(422,'Nieprawidłowy filtr')
    from backend.native_queries import tasks_page
    return tasks_page(db,user,representative_id,limit,offset,search=search,priority=priority,status=status,from_date=from_date,to_date=to_date)

@router.get('/visits/page')
def visits_page(day:str='',days:int=1,representative_id:str='',search:str='',priority:str='',status:str='',limit:int=20,offset:int=0,user=Depends(current),db=Depends(database)):
    require()
    from backend.native_queries import bounds,scope
    from sqlalchemy import func
    bounds(limit,offset);scope(user,representative_id)
    if days not in (1,7,28,29,30,31) or len(search)>160 or priority not in ('','A+','A','B','C') or status not in ('','proposed','confirmed','completed','cancelled'):raise HTTPException(422,'Nieprawidłowy filtr planu')
    d=day_value(day);start=datetime.combine(d,time.min,ZONE).astimezone(timezone.utc);end=datetime.combine(d+timedelta(days=days),time.min,ZONE).astimezone(timezone.utc)
    q=select(Appointment,Salon).join(Salon,Salon.id==Appointment.salon_id).join(User,User.id==Appointment.user_id).where(Appointment.starts_at>=start.isoformat(),Appointment.starts_at<end.isoformat())
    if user.role!='manager':q=q.where(Salon.owner_id==user.id,Appointment.user_id==user.id)
    if representative_id:q=q.where(Appointment.user_id==representative_id)
    if priority:q=q.where(Salon.priority==priority)
    if status:q=q.where(Appointment.status==status)
    if search:q=q.where((func.strpos(func.lower(Salon.name),search.lower())>0) | (func.strpos(func.lower(User.name),search.lower())>0))
    total=db.scalar(select(func.count()).select_from(q.subquery()))
    from backend.visit_planner import verified,links,revision
    items=[{**{k:getattr(a,k) for k in ('id','salon_id','user_id','starts_at','ends_at','status','notes')},'salon_name':s.name,'city':s.city,'address':s.address,'revision':revision(a),**links(a,s,verified(db,s))} for a,s in db.execute(q.order_by(Appointment.starts_at,Appointment.id).limit(limit).offset(offset))]
    return {'items':items,'total':total,'limit':limit,'offset':offset,'has_more':offset+limit<total}

def reminders(db):
    from backend.native_notifications import generate
    return generate(db)

@router.get('/notifications')
def notifications(response:Response,limit:int=100,offset:int=0,user=Depends(current),db=Depends(database)):
    require()
    from backend.native_notifications import page
    data=page(db,user,limit,offset)
    response.headers['X-Focus-Total']=str(data['total']);response.headers['X-Focus-Has-More']=str(data['has_more']).lower()
    return data['items']

@router.get('/notifications/page')
def notifications_paged(limit:int=20,offset:int=0,user=Depends(current),db=Depends(database)):
    require()
    from backend.native_notifications import page
    return page(db,user,limit,offset)
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
