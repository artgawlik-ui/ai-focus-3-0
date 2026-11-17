"""Optional Google Calendar: user OAuth + approved durable synchronization. OFF by default."""
import base64,hashlib,json,os,secrets,uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode,urlsplit
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel,Field
from sqlalchemy import select,update,text
from sqlalchemy.exc import IntegrityError
from backend.db import Session,User,Appointment,Salon,Activity,now
from backend.security import current,manager,database,digest
from backend.google_models import GoogleOAuthState,GoogleAccount,GoogleEventLink,GoogleSyncRequest
from backend import google_transport as transport
from backend.visit_planner import revision,verified
from backend.calendar_preview import google_event

router=APIRouter(prefix='/api/google-calendar',tags=['Google Calendar'])

def uid():return str(uuid.uuid4())
def hash_payload(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def require():
    if not transport.enabled():raise HTTPException(404,'Integracja Google wyłączona')

def configuration():
    require()
    expected=os.getenv('APP_ORIGIN','').rstrip('/')+'/api/google-calendar/oauth/callback'
    if not all(os.getenv(k) for k in ('GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_REDIRECT_URI','GOOGLE_ENCRYPTION_KEY')) or not (expected.startswith('https://') or (os.getenv('APP_ENV')=='test' and urlsplit(expected).hostname in ('localhost','127.0.0.1') and expected.startswith('http://'))) or os.getenv('GOOGLE_REDIRECT_URI')!=expected:
        raise HTTPException(503,'Brak bezpiecznej konfiguracji Google')
    try:transport.cipher()
    except transport.ProviderError:raise HTTPException(503,'Nieprawidłowa konfiguracja szyfrowania') from None

def lifecycle(db,user_id):
    if db.bind.dialect.name=='postgresql':db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':'focus3-google-lifecycle:'+user_id})

def account_status(a):
    return {'connected':bool(a and a.tokens_ciphertext and not a.revoked),'approved':bool(a and a.approved),'calendar_bound':bool(a and a.calendar_id and not a.revoked),'status':a.status if a else 'not_connected'}

@router.get('/status')
def status(user=Depends(current),db=Depends(database)):
    a=db.get(GoogleAccount,user.id) if transport.schema() else None
    return {'enabled':transport.enabled(),'schema_enabled':transport.schema(),'writes_enabled':transport.writable(),'oauth_configured':all(os.getenv(k) for k in ('GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_REDIRECT_URI','GOOGLE_ENCRYPTION_KEY')),**account_status(a)}

@router.post('/oauth/start')
def start(request:Request,user=Depends(current),db=Depends(database)):
    configuration()
    state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    db.add(GoogleOAuthState(state_hash=digest(state),user_id=user.id,session_hash=digest(request.cookies.get('focus_session','')),verifier_ciphertext=transport.seal({'verifier':verifier}),expires_at=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()))
    db.commit()
    url='https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':os.environ['GOOGLE_CLIENT_ID'],'redirect_uri':os.environ['GOOGLE_REDIRECT_URI'],'response_type':'code','scope':transport.SCOPE,'access_type':'offline','prompt':'consent select_account','state':state,'code_challenge':challenge,'code_challenge_method':'S256','include_granted_scopes':'false'})
    return {'authorization_url':url}

@router.get('/oauth/callback')
def callback(request:Request,state:str='',code:str='',error:str='',error_reason:str='',user=Depends(current),db=Depends(database)):
    configuration()
    if not state or len(state)>512 or len(code)>4096:raise HTTPException(403,'Nieprawidłowa autoryzacja Google')
    row=db.scalar(select(GoogleOAuthState).where(GoogleOAuthState.state_hash==digest(state)).with_for_update())
    if not row or row.consumed or row.user_id!=user.id or row.session_hash!=digest(request.cookies.get('focus_session','')) or row.expires_at<now():raise HTTPException(403,'Nieprawidłowa autoryzacja Google')
    try:verifier=transport.unseal(row.verifier_ciphertext)['verifier']
    except Exception:raise HTTPException(503,'Stan autoryzacji niedostępny') from None
    row.consumed=1;row.verifier_ciphertext=''
    if code:row.code_hash=digest(code)
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(403,'Kod został już użyty') from None
    result='cancelled' if error or error_reason or not code else 'failed'
    if result!='cancelled':
        try:
            data=transport.token_post({'code':code,'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET'],'redirect_uri':os.environ['GOOGLE_REDIRECT_URI'],'grant_type':'authorization_code','code_verifier':verifier})
            value=transport.tokens(data)
            lifecycle(db,user.id)
            a=db.scalar(select(GoogleAccount).where(GoogleAccount.user_id==user.id).with_for_update())
            live_user=db.get(User,user.id,populate_existing=True,with_for_update={'key_share':True})
            live_state=db.get(GoogleOAuthState,digest(state),populate_existing=True,with_for_update=True)
            if not live_user.active or live_state.cancelled or live_state.expires_at<now():raise transport.ProviderError('authorization_cancelled')
            if not a:a=GoogleAccount(user_id=user.id,generation=0);db.add(a)
            a.generation+=1;a.tokens_ciphertext=transport.seal(value);a.calendar_id='';a.approved=0;a.approved_by=None;a.approved_at='';a.revoked=0;a.status='awaiting_approval';a.updated_at=now()
            db.commit();result='connected'
        except transport.ProviderError:db.rollback()
    response=RedirectResponse('/?google_calendar='+result,status_code=303)
    response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
    return response

@router.get('/accounts')
def accounts(user=Depends(manager),db=Depends(database)):
    require()
    return [{'user_id':u.id,'name':u.name,**account_status(a)} for a,u in db.execute(select(GoogleAccount,User).join(User,User.id==GoogleAccount.user_id))]

@router.post('/accounts/{user_id}/approve')
def approve(user_id:str,user=Depends(manager),db=Depends(database)):
    require();a=db.scalar(select(GoogleAccount).where(GoogleAccount.user_id==user_id).with_for_update())
    target=db.get(User,user_id)
    if not target or not target.active:raise HTTPException(409,'Użytkownik nieaktywny')
    if not a or a.revoked or not a.tokens_ciphertext:raise HTTPException(409,'Najpierw autoryzuj konto użytkownika')
    if a.approved:return account_status(a)
    a.approved=1;a.approved_by=user.id;a.approved_at=now();a.updated_at=now();a.status='approved' if not a.calendar_id else 'ready';db.commit()
    return account_status(a)

@router.post('/accounts/{user_id}/calendar')
def create_calendar(user_id:str,user=Depends(manager),db=Depends(database)):
    require()
    if not transport.writable():raise HTTPException(403,'Transport zapisu Google wyłączony')
    a=db.scalar(select(GoogleAccount).where(GoogleAccount.user_id==user_id).with_for_update())
    target=db.get(User,user_id)
    if not target or not target.active or not a or not a.approved or a.revoked:raise HTTPException(409,'Konto wymaga zatwierdzenia')
    if a.calendar_id:return {'calendar_bound':True,'created':False}
    if a.status in ('calendar_creating','calendar_creation_uncertain'):raise HTTPException(409,'Niepewny wynik tworzenia; wymagana ręczna weryfikacja, bez ponowienia')
    generation=a.generation
    a.status='calendar_creating';db.commit()
    a=db.scalar(select(GoogleAccount).where(GoogleAccount.user_id==user_id).with_for_update().execution_options(populate_existing=True))
    people={u.id:u for u in db.scalars(select(User).where(User.id.in_([user_id,user.id])).order_by(User.id).with_for_update(key_share=True))}
    if not people.get(user_id) or not people[user_id].active or not people[user.id].active or people[user.id].role!='manager':raise HTTPException(409,'Dostęp odwołany')
    if a.generation!=generation or a.revoked or not a.approved or a.status!='calendar_creating':raise HTTPException(409,'Powiązanie zmienione')
    try:
        _,data=transport.calendar_request(a,'POST','calendars',{'summary':'Ai Focus · wizyty','timeZone':'Europe/Warsaw'})
        identity=data.get('id')
        if not isinstance(identity,str) or not identity or len(identity)>300 or identity=='primary':raise transport.ProviderError('provider_invalid_response')
        a.calendar_id=identity;a.status='ready';a.updated_at=now();db.commit()
        return {'calendar_bound':True,'created':True}
    except transport.ProviderError as e:
        # Calendar insert has no caller-chosen ID. Never blindly retry an ambiguous create.
        if e.code not in ('account_disabled','reauthorization_required','transport_disabled','oauth_disabled','credential_unavailable','encryption_configuration'):
            a.status='calendar_creation_uncertain'
        db.commit();raise HTTPException(503,'Nie potwierdzono utworzenia kalendarza; sprawdź diagnostykę') from None


def payload(db,appointment,account):
    salon=db.get(Salon,appointment.salon_id)
    data=google_event(appointment,salon,verified(db,salon))
    data['id']='focus3'+hash_payload([account.user_id,account.generation,account.calendar_id,appointment.id])
    data.setdefault('location','')
    if appointment.status=='cancelled':data={k:data[k] for k in ('id','status','extendedProperties')}
    return data

class SyncIn(BaseModel):
    request_id:uuid.UUID
    approval_revision:str=Field(min_length=64,max_length=64)
    approval_payload_hash:str=Field(min_length=64,max_length=64)

@router.get('/sync-preview/{appointment_id}')
def sync_preview(appointment_id:str,user=Depends(manager),db=Depends(database)):
    require();a=db.get(Appointment,appointment_id)
    if not a:raise HTTPException(404,'Brak wizyty')
    account=db.get(GoogleAccount,a.user_id)
    if not account or account.revoked or not account.approved or not account.calendar_id:raise HTTPException(409,'Najpierw przygotuj kalendarz handlowca')
    data=payload(db,a,account)
    return {'mode':'preview','external_write':False,'approval_revision':revision(a),'payload_hash':hash_payload(data),'event':data,'representative_name':db.get(User,a.user_id).name}

@router.post('/sync/{appointment_id}',status_code=202)
def enqueue(appointment_id:str,body:SyncIn,user=Depends(manager),db=Depends(database)):
    require()
    a=db.get(Appointment,appointment_id)
    if not a:raise HTTPException(404,'Brak wizyty')
    account=db.scalar(select(GoogleAccount).where(GoogleAccount.user_id==a.user_id).with_for_update())
    a=db.scalar(select(Appointment).where(Appointment.id==appointment_id).with_for_update().execution_options(populate_existing=True))
    if not account or account.revoked or not account.approved or not account.calendar_id:raise HTTPException(409,'Kalendarz użytkownika niegotowy')
    if a.status not in ('confirmed','cancelled'):raise HTTPException(409,'Synchronizuj zatwierdzoną wizytę lub jej odwołanie')
    if body.approval_revision!=revision(a):raise HTTPException(409,'Wizyta została zmieniona; zatwierdź bieżącą wersję')
    data=payload(db,a,account);stamp=hash_payload(data)
    if body.approval_payload_hash!=stamp:raise HTTPException(409,'Wizyta lub profil zmienione; sprawdź podgląd ponownie')
    link=db.get(GoogleEventLink,a.id)
    if link and (link.user_id!=a.user_id or link.generation!=account.generation or link.calendar_id!=account.calendar_id):raise HTTPException(409,'Powiązanie konta zmienione; wymagany przegląd')
    existing=db.get(GoogleSyncRequest,str(body.request_id))
    if existing:
        if existing.appointment_id!=a.id or existing.payload_hash!=stamp or existing.generation!=account.generation or existing.local_revision!=revision(a):raise HTTPException(409,'Identyfikator żądania już użyty')
        return {'id':existing.id,'status':existing.status}
    pending=db.scalar(select(GoogleSyncRequest).where(GoogleSyncRequest.appointment_id==a.id,GoogleSyncRequest.generation==account.generation,GoogleSyncRequest.payload_hash==stamp,GoogleSyncRequest.local_revision==revision(a),GoogleSyncRequest.status.in_(('pending','retry'))))
    if pending:return {'id':pending.id,'status':pending.status}
    if link and link.payload_hash==stamp:return {'id':None,'status':'already_synced'}
    job=GoogleSyncRequest(id=str(body.request_id),appointment_id=a.id,user_id=a.user_id,requested_by=user.id,generation=account.generation,payload_hash=stamp,local_revision=revision(a),payload_ciphertext=transport.seal(data),expires_at=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat())
    db.add(job);db.commit()
    return {'id':job.id,'status':job.status}

@router.get('/requests')
def requests(user=Depends(current),db=Depends(database)):
    require();query=select(GoogleSyncRequest)
    if user.role!='manager':query=query.where(GoogleSyncRequest.user_id==user.id)
    result=[]
    for j in db.scalars(query.order_by(GoogleSyncRequest.created_at.desc()).limit(100)):
        a=db.get(Appointment,j.appointment_id);account=db.get(GoogleAccount,j.user_id)
        matches=bool(a and account and account.generation==j.generation and revision(a)==j.local_revision and hash_payload(payload(db,a,account))==j.payload_hash)
        result.append({'id':j.id,'appointment_id':j.appointment_id,'status':j.status,'attempts':j.attempts,'last_error':j.last_error,'updated_at':j.updated_at,'matches_local_version':matches})
    return result

@router.post('/disconnect')
def disconnect(user=Depends(current),db=Depends(database)):
    if not transport.schema():return {'disconnected':True,'remote_revocation':'not_attempted'}
    lifecycle(db,user.id)
    a=db.scalar(select(GoogleAccount).where(GoogleAccount.user_id==user.id).with_for_update())
    if a:
        a.revoked=1;a.tokens_ciphertext='';a.approved=0;a.approved_by=None;a.approved_at='';a.generation+=1;a.status='disconnected';a.updated_at=now()
        db.execute(update(GoogleSyncRequest).where(GoogleSyncRequest.user_id==user.id,GoogleSyncRequest.status.in_(('pending','retry'))).values(status='cancelled',payload_ciphertext='',last_error='account_disconnected',updated_at=now()))
    db.execute(update(GoogleOAuthState).where(GoogleOAuthState.user_id==user.id).values(consumed=1,cancelled=1,verifier_ciphertext=''))
    db.commit()
    return {'disconnected':True,'remote_revocation':'not_attempted'}


def same_event(actual,expected):
    if actual.get('id')!=expected['id']:return False
    if expected['status']=='cancelled':return actual.get('status')=='cancelled'
    try:
        dates=all(datetime.fromisoformat(actual[k]['dateTime']).astimezone(timezone.utc)==datetime.fromisoformat(expected[k]['dateTime']).astimezone(timezone.utc) for k in ('start','end'))
        return dates and actual.get('summary')==expected['summary'] and actual.get('status')==expected['status'] and actual.get('location','')==expected.get('location','') and actual.get('extendedProperties',{}).get('private',{}).get('focus3AppointmentId')==expected['extendedProperties']['private']['focus3AppointmentId']
    except Exception:return False


def synchronize(account,link,data):
    path=transport.event_path(account.calendar_id,data['id'])
    code,remote=transport.calendar_request(account,'GET',path)
    if code in (404,410):
        if link:raise transport.ProviderError('remote_missing')
        if data['status']=='cancelled':return None
        code,remote=transport.calendar_request(account,'POST',transport.event_path(account.calendar_id),data)
        if code==409:
            _,remote=transport.calendar_request(account,'GET',path)
        elif code not in (200,201):raise transport.ProviderError('provider_invalid_response')
    else:
        owned=remote.get('extendedProperties',{}).get('private',{}).get('focus3AppointmentId')==data['extendedProperties']['private']['focus3AppointmentId']
        if not owned and not (link and remote.get('status')=='cancelled'):raise transport.ProviderError('remote_ownership_conflict')
        if link and remote.get('etag')!=link.etag:raise transport.ProviderError('remote_conflict')
        if not same_event(remote,data):
            if not link:raise transport.ProviderError('remote_conflict')
            _,remote=transport.calendar_request(account,'PATCH',path,{'status':'cancelled'} if data['status']=='cancelled' else {k:v for k,v in data.items() if k!='id'},remote.get('etag'))
    if not same_event(remote,data) or not isinstance(remote.get('etag'),str) or not remote['etag']:raise transport.ProviderError('provider_unconfirmed')
    return remote


def process_once():
    if not transport.writable():return False
    with Session() as db:
        # Account -> request ordering matches disconnect, approval and enqueue.
        candidate=db.scalar(select(GoogleSyncRequest.user_id).where(GoogleSyncRequest.status.in_(('pending','retry')),GoogleSyncRequest.next_attempt_at<=now()).order_by(GoogleSyncRequest.created_at).limit(1))
        if not candidate:return False
        account=db.scalar(select(GoogleAccount).where(GoogleAccount.user_id==candidate).with_for_update(skip_locked=True))
        if not account:return False
        job=db.scalar(select(GoogleSyncRequest).where(GoogleSyncRequest.user_id==candidate,GoogleSyncRequest.status.in_(('pending','retry')),GoogleSyncRequest.next_attempt_at<=now()).order_by(GoogleSyncRequest.created_at).with_for_update(skip_locked=True).limit(1))
        if not job:return False
        try:
            a=db.get(Appointment,job.appointment_id)
            if a and a.status!='cancelled':
                from backend.contact_guard import lock_contact
                lock_contact(db,a.salon_id)
            people={u.id:u for u in db.scalars(select(User).where(User.id.in_([job.requested_by,job.user_id])).order_by(User.id).with_for_update(key_share=True))}
            a=db.scalar(select(Appointment).where(Appointment.id==job.appointment_id).with_for_update().execution_options(populate_existing=True))
            requester=people.get(job.requested_by);representative=people.get(job.user_id)
            if not requester or not requester.active or requester.role!='manager' or not representative or not representative.active:raise transport.ProviderError('approval_access_revoked')
            if job.expires_at<now():raise transport.ProviderError('approval_expired')
            if account.revoked or not account.approved or account.generation!=job.generation:raise transport.ProviderError('account_changed')
            if not a or a.user_id!=job.user_id or a.status not in ('confirmed','cancelled'):raise transport.ProviderError('appointment_changed')
            salon=db.get(Salon,a.salon_id,populate_existing=True,with_for_update={'key_share':True})
            if a.status!='cancelled':
                from backend.meta_models import MetaConversation
                if salon.owner_id!=a.user_id or salon.status=='do_not_contact' or db.scalar(select(MetaConversation.id).where(MetaConversation.salon_id==salon.id,MetaConversation.opted_out==1).limit(1)):raise transport.ProviderError('contact_blocked')
            data=payload(db,a,account)
            if revision(a)!=job.local_revision or hash_payload(data)!=job.payload_hash:raise transport.ProviderError('appointment_changed')
            link=db.get(GoogleEventLink,a.id)
            if link and (link.user_id!=account.user_id or link.generation!=account.generation or link.calendar_id!=account.calendar_id):raise transport.ProviderError('account_changed')
            job.attempts+=1
            if a.status=='cancelled' and not link:
                job.status='not_required'
            else:
                remote=synchronize(account,link,data)
                if remote is None:job.status='not_required'
                else:
                    if not link:link=GoogleEventLink(appointment_id=a.id,user_id=a.user_id,generation=account.generation,calendar_id=account.calendar_id,event_id=data['id'],etag=remote['etag'],payload_hash=job.payload_hash,status=remote['status']);db.add(link)
                    else:link.etag=remote['etag'];link.payload_hash=job.payload_hash;link.status=remote['status'];link.updated_at=now()
                    job.status='synced'
                    db.add(Activity(id=uid(),salon_id=a.salon_id,user_id=job.requested_by,kind='calendar_sync',body='Potwierdzono stan wizyty w dedykowanym kalendarzu Google.'))
            job.payload_ciphertext='';job.last_error='';job.updated_at=now();db.commit()
        except transport.ProviderError as e:
            job.status='retry' if e.retry and job.attempts<5 else 'needs_review'
            job.last_error=e.code;job.updated_at=now();job.next_attempt_at=(datetime.now(timezone.utc)+timedelta(seconds=min(300,5*2**min(job.attempts,6)))).isoformat()
            if job.status!='retry':job.payload_ciphertext=''
            db.commit()
        return True
