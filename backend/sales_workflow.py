"""Operator-declared Instagram contact; no network transport, no Meta receipts."""
import hashlib,json,os,re,uuid
from datetime import datetime,timedelta,timezone
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from backend.db import Salon,Activity,now
from backend.security import current,database
from backend.contact_guard import lock_contact

router=APIRouter(prefix='/api/salons',tags=['Ręczny kontakt Instagram'])
KINDS=('sales_profile','sales_draft','sales_not_sent','instagram_manual','instagram_reply_manual','sales_refused')
def enabled():return os.getenv('SALES_WORKFLOW_ENABLED','').strip().lower()=='true'
def require():
    if not enabled():raise HTTPException(404,'Proces ręczny wyłączony')
def handle(value):
    value=value.strip()
    if value.startswith('https://'):
        u=urlsplit(value)
        if u.netloc not in ('instagram.com','www.instagram.com') or u.query or u.fragment:raise HTTPException(422,'Wymagany bezpośredni profil Instagram')
        value=u.path.strip('/')
    value=value.removeprefix('@').lower()
    if not re.fullmatch(r'[a-z0-9_](?:[a-z0-9_.]{0,28}[a-z0-9_])?',value) or '..' in value or value in ('accounts','direct','explore','reels','stories','p'):
        raise HTTPException(422,'Nieprawidłowy profil Instagram')
    return value

def snapshot(s):
    return hashlib.sha256(json.dumps([s.name,s.city,s.instagram,s.source_url,s.specialization],ensure_ascii=False).encode()).hexdigest()
def access(db,id,user,write=False):
    if write:lock_contact(db,id)
    s=db.get(Salon,id,populate_existing=True,with_for_update=write)
    if not s or (user.role!='manager' and s.owner_id!=user.id):raise HTTPException(404,'Brak salonu')
    return s

def history(db,s):return list(db.scalars(select(Activity).where(Activity.salon_id==s.id,Activity.kind.in_(KINDS)).order_by(Activity.created_at,Activity.id)))
def data(a):
    # Older Meta audits share instagram_manual but contain plain text, not this envelope.
    try:
        value=json.loads(a.body)
        if isinstance(value,dict):return value
    except (ValueError,TypeError):pass
    return {'note':a.body,'source':'legacy_crm_activity','api_confirmed_sent':False}
def add(db,s,user,kind,payload,id=None):
    a=Activity(id=id or str(uuid.uuid4()),salon_id=s.id,user_id=user.id,kind=kind,body=json.dumps(payload,ensure_ascii=False));db.add(a);db.flush();return a

def is_blocked(db,s):
    from backend.meta_models import MetaConversation
    return s.status=='do_not_contact' or bool(db.scalar(select(MetaConversation.id).where(MetaConversation.salon_id==s.id,MetaConversation.opted_out==1).limit(1)))
def contact_allowed(db,s):
    if is_blocked(db,s):raise HTTPException(409,'Kontakt zablokowany')
def verified(s,rows):return any(a.kind=='sales_profile' and data(a).get('snapshot')==snapshot(s) for a in rows)
def public(a):return {'id':a.id,'kind':a.kind,'at':a.created_at,'author_id':a.user_id,'source':data(a).get('source','operator_declaration'),'details':data(a)}

@router.get('/{id}/instagram-contact')
def state(id:str,user=Depends(current),db=Depends(database)):
    require();s=access(db,id,user);rows=history(db,s)
    try:url='https://www.instagram.com/'+handle(s.instagram)+'/'
    except HTTPException:url=None
    return {'can_confirm_sent':user.role=='manager' and user.email.casefold()==os.getenv('BOOTSTRAP_EMAIL','').casefold(),'sender':'@artur_uluru_hair','profile_url':url,'profile_verified':verified(s,rows),'events':[public(a) for a in rows], 'outbound':False,'api_confirmed_sent':False,'blocked':is_blocked(db,s)}

class VerifyIn(BaseModel):
    profile:str=Field(min_length=1,max_length=150)
    evidence:str=Field(min_length=10,max_length=500)
    identity_confirmed:bool=False
@router.post('/{id}/verify-instagram')
def verify(id:str,p:VerifyIn,user=Depends(current),db=Depends(database)):
    require();s=access(db,id,user,True)
    if not p.identity_confirmed or handle(p.profile)!=handle(s.instagram):raise HTTPException(409,'Profil nie zgadza się z CRM lub nie potwierdzono tożsamości')
    rows=history(db,s)
    if not verified(s,rows):add(db,s,user,'sales_profile',{'snapshot':snapshot(s),'profile':handle(s.instagram),'evidence':p.evidence})
    db.commit();return {'verified':True}

@router.post('/{id}/prepare-instagram',status_code=201)
def prepare(id:str,user=Depends(current),db=Depends(database)):
    require();s=access(db,id,user,True);contact_allowed(db,s);rows=history(db,s)
    if not verified(s,rows):raise HTTPException(409,'Najpierw ręcznie zweryfikuj profil i dane CRM')
    # Any earlier confirmed contact requires human review, never another cold attempt.
    recent=db.scalar(select(Activity.id).where(Activity.salon_id==s.id,Activity.kind.in_(('call','visit','follow_up','email_received','instagram_received','instagram_manual','instagram_reply_manual'))).limit(1))
    if recent:raise HTTPException(409,'Istnieje kontakt; przejrzyj historię zamiast ponawiać pierwszy DM')
    old=next((a for a in reversed(rows) if a.kind=='sales_draft'),None)
    if old and data(old)['snapshot']==snapshot(s):return public(old)
    from backend.qualification import analyze
    result=analyze(s,[])
    a=add(db,s,user,'sales_draft',{'snapshot':snapshot(s),'text':result['draft'],'priority':result['priority_suggestion'],'sources':result['sources'],'sent':False})
    db.commit();return public(a)

class EventIn(BaseModel):
    draft_id:str
    request_id:uuid.UUID
    action:Literal['not_sent','manual_sent','replied','refused']
    confirmed:bool=False
    note:str=Field(min_length=3,max_length=2000)
    customer_initiated:bool=False

@router.post('/{id}/instagram-events')
def record_event(id:str,p:EventIn,user=Depends(current),db=Depends(database)):
    require();s=access(db,id,user,True);rows=history(db,s)
    event_id=str(uuid.uuid5(uuid.NAMESPACE_URL,s.id+':'+str(p.request_id)))
    old=next((a for a in rows if a.id==event_id),None)
    if old:
        if data(old).get('action')!=p.action or data(old).get('draft_id')!=p.draft_id or data(old).get('note')!=p.note or data(old).get('customer_initiated')!=(p.customer_initiated if p.action=='replied' else False):raise HTTPException(409,'Identyfikator operacji już wykorzystany')
        return public(old)
    draft=next((a for a in rows if a.id==p.draft_id and a.kind=='sales_draft'),None)
    if not draft:raise HTTPException(404,'Brak szkicu')
    if not p.confirmed:raise HTTPException(422,'Wymagane jawne potwierdzenie rzeczywistego zdarzenia')
    previous=[a for a in rows if data(a).get('draft_id')==draft.id]
    sent=any(a.kind=='instagram_manual' for a in previous)
    if p.action in ('manual_sent','not_sent'):
        contact_allowed(db,s)
        if sent:raise HTTPException(409,'Kontakt już zarejestrowany; nie ponawiaj')
    if p.action=='manual_sent':
        from backend.meta import owner
        owner(user)
        if not verified(s,rows) or data(draft)['snapshot']!=snapshot(s) or draft.created_at<(datetime.now(timezone.utc)-timedelta(days=7)).isoformat():raise HTTPException(409,'Szkic lub profil wymaga ponownej weryfikacji')
        # Cross-channel contact after drafting also blocks another first message.
        if db.scalar(select(Activity.id).where(Activity.salon_id==s.id,Activity.kind.in_(('call','visit','follow_up','email_received','instagram_received','instagram_manual','instagram_reply_manual'))).limit(1)):
            raise HTTPException(409,'Historia zawiera kontakt; nie ponawiaj pierwszej wiadomości')
        if s.stage=='new':s.stage='contacted'
    if p.action in ('replied','refused'):
        if any(a.kind=='sales_refused' or (p.action=='replied' and a.kind=='instagram_reply_manual') for a in previous):raise HTTPException(409,'Odpowiedź już zarejestrowana')
        if not sent:raise HTTPException(409,'Najpierw potwierdź rzeczywisty kontakt; odpowiedzi API są osobną historią')
        if p.action=='refused':s.status='do_not_contact'
        else:
            contact_allowed(db,s)
            if s.stage in ('new','contacted'):s.stage='discovery'
    kind={'not_sent':'sales_not_sent','manual_sent':'instagram_manual','replied':'instagram_reply_manual','refused':'sales_refused'}[p.action]
    a=add(db,s,user,kind,{'action':p.action,'draft_id':draft.id,'note':p.note,'customer_initiated':p.customer_initiated if p.action=='replied' else False,'api_confirmed_sent':False,'source':'operator_declaration'},event_id)
    if p.action=='replied':
        from backend.native_planning import enabled as native_enabled
        if native_enabled():
            from backend.native_models import Task
            db.add(Task(id=str(uuid.uuid4()),salon_id=s.id,assignee_id=s.owner_id,title='Przejrzyj odpowiedź i uzgodnij wizytę' if p.customer_initiated else 'Przejrzyj odpowiedź klienta',due_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),cycle_key='sales-reply:'+a.id))
    s.version+=1;s.updated_at=now();db.commit();return public(a)
