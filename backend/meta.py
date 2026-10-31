"""Official Instagram Login, signed inbound webhooks, owner-reviewed drafts.
Development accounts only. No network method for sending messages exists.
Credentials are encrypted in PostgreSQL; only the encryption key is in the environment.
Unified Login uses business integration system-user tokens, not Instagram User tokens.
"""
import hashlib,hmac,json,logging,os,secrets,uuid
from datetime import datetime,timedelta,timezone
from urllib.parse import urlencode
from types import SimpleNamespace
import httpx
from cryptography.fernet import Fernet,InvalidToken
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import BaseModel,Field
from sqlalchemy import select,update,delete,func
from sqlalchemy.exc import IntegrityError
from backend.db import Session,Salon,Activity,LoginSession,User,now
from backend.security import current,manager,database,digest
from backend.meta_models import MetaOAuthState,MetaConversation,MetaMessage,MetaCredential,MetaPrivacyRequest
router=APIRouter(prefix='/api/meta',tags=['Instagram development'])
SCOPES={'instagram_basic','instagram_manage_messages'}
GRAPH='https://graph.facebook.com/v26.0'
TARGET_USERNAME='artur_uluru_hair'
uid=lambda:str(uuid.uuid4())
# Official exchange/refresh endpoints require secret-bearing query parameters.
# Never allow httpx INFO logging of those URLs.
logging.getLogger('httpx').setLevel(logging.WARNING)

def enabled():return os.getenv('META_ENABLED','false').lower()=='true'
def require_config():
    if not enabled():raise HTTPException(404,'Integracja Meta wyłączona')
    if os.getenv('META_MODE')!='development':raise HTTPException(409,'Dozwolony wyłącznie tryb deweloperski')
    missing=[k for k in ('META_APP_ID','META_APP_SECRET','META_CONFIG_ID','META_VERIFY_TOKEN','META_ENCRYPTION_KEY','META_TEST_ACCOUNT_ID','META_REDIRECT_URI') if not os.getenv(k)]
    if missing:raise HTTPException(503,'Brak bezpiecznej konfiguracji integracji')
    try:Fernet(os.environ['META_ENCRYPTION_KEY'].encode())
    except Exception:raise HTTPException(503,'Nieprawidłowy klucz szyfrowania integracji')
    if not os.environ['META_REDIRECT_URI'].startswith('https://'):raise HTTPException(503,'OAuth wymaga HTTPS')

def seal(kind,value):return Fernet(os.environ['META_ENCRYPTION_KEY'].encode()).encrypt(json.dumps({'kind':kind,'value':value}).encode()).decode()
def unseal(kind,value):
    try:
        data=json.loads(Fernet(os.environ['META_ENCRYPTION_KEY'].encode()).decrypt(value.encode()))
        if data['kind']!=kind:raise ValueError()
        return data['value']
    except (InvalidToken,ValueError,KeyError):raise HTTPException(503,'Sekret integracji niedostępny; wymagana ponowna autoryzacja')
def credentials(db):
    row=db.get(MetaCredential,os.environ['META_TEST_ACCOUNT_ID'])
    if not row or row.revoked or not row.token_ciphertext or (row.expires_at and row.expires_at<=now()):return None
    if not isinstance(unseal('token',row.token_ciphertext),str):raise HTTPException(503,'Nieprawidłowy magazyn tokenów')
    return row

def graph_headers(token):return {'Authorization':'Bearer '+token}
class InvalidMetaGrant(ValueError):pass

def validate_token(client,token):
    r=client.get(GRAPH+'/debug_token',params={'input_token':token},headers=graph_headers(os.environ['META_APP_ID']+'|'+os.environ['META_APP_SECRET']));r.raise_for_status();data=r.json()['data']
    if not data.get('is_valid') or str(data.get('app_id'))!=os.environ['META_APP_ID'] or not SCOPES<=set(data.get('scopes',[])) or set(data.get('scopes',[]))-SCOPES-{'public_profile'}:raise InvalidMetaGrant('Invalid grant')
    if data.get('type') not in ('SYSTEM_USER','BUSINESS_INTEGRATION_SYSTEM_USER'):raise InvalidMetaGrant('Unified Login requires system-user configuration')
    expiry=min((int(data[k]) for k in ('expires_at','data_access_expires_at') if data.get(k)),default=0)
    data['expires_at']=expiry
    if expiry and expiry<=int(datetime.now(timezone.utc).timestamp()):raise InvalidMetaGrant('Expired')
    return data

def owner(user):
    if user.role!='manager' or user.email.casefold()!=os.getenv('BOOTSTRAP_EMAIL','').casefold():raise HTTPException(403,'Wymagana akceptacja właściciela')

def conversation_access(db,id,user,lock=False):
    statement=select(MetaConversation).where(MetaConversation.id==id)
    if lock:statement=statement.with_for_update()
    c=db.scalar(statement.execution_options(populate_existing=True))
    if not c:raise HTTPException(404,'Konwersacja niedostępna')
    salon=db.get(Salon,c.salon_id) if c.salon_id else None
    if user.role!='manager' and (not salon or salon.owner_id!=user.id):raise HTTPException(404,'Konwersacja niedostępna')
    return c

def audit(db,c,user_id,kind,body):
    if c.salon_id:db.add(Activity(id=uid(),salon_id=c.salon_id,user_id=user_id,kind=kind,body=body))

def opt_out(text):return any(p in text.casefold() for p in ('nie kontakt','usuń moje','usun moje','nie życzę','nie zycze','stop'))

def public_message(m):
    return {'id':m.id,'external_id':m.external_id,'status':m.status,'direction':m.direction,'text':unseal('message',m.body_ciphertext) if m.body_ciphertext and m.occurred_at>(datetime.now(timezone.utc)-timedelta(days=30)).isoformat() else '', 'occurred_at':m.occurred_at,'approved_by':m.approved_by}

@router.get('/status')
def status(user=Depends(current),db=Depends(database)):
    data={'enabled':enabled(),'connected':False,'mode':'development_only','oauth_path':'unified_login','graph_version':'v26.0','outbound':False,'account_verified':False,'required_scopes':sorted(SCOPES),'credential_storage':'encrypted_postgresql; encryption key in environment','target_account_status':'not_authorized','delivery_status_supported':False,'can_approve':user.role=='manager' and user.email.casefold()==os.getenv('BOOTSTRAP_EMAIL','').casefold()}
    if not enabled():return data
    require_config();token=credentials(db)
    data.update(connected=bool(token),account_verified=bool(token),expires_at=token.expires_at if token else None,reauthorization_required=not bool(token))
    return data

@router.post('/oauth/start')
def oauth_start(request:Request,response:Response,user=Depends(manager),db=Depends(database)):
    require_config();owner(user)
    if db.scalar(select(func.count()).select_from(MetaOAuthState).where(MetaOAuthState.user_id==user.id,MetaOAuthState.expires_at>now(),MetaOAuthState.consumed==0))>=3:raise HTTPException(429,'Zbyt wiele rozpoczętych autoryzacji')
    state=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32)
    db.execute(delete(MetaOAuthState).where(MetaOAuthState.expires_at<now()))
    db.add(MetaOAuthState(state_hash=digest(state),nonce_hash=digest(nonce),session_hash=digest(request.cookies['focus_session']),user_id=user.id,expires_at=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()));db.commit()
    response.set_cookie('focus_meta_oauth',nonce,httponly=True,secure=True,samesite='lax',max_age=600,path='/api/meta/oauth/callback')
    return {'authorization_url':'https://www.facebook.com/dialog/oauth?'+urlencode({'client_id':os.environ['META_APP_ID'],'config_id':os.environ['META_CONFIG_ID'],'redirect_uri':os.environ['META_REDIRECT_URI'],'response_type':'code','state':state,'prompt':'login'})}

@router.get('/oauth/callback')
def oauth_callback(request:Request,response:Response,state:str='',code:str='',error:str='',error_reason:str='',db=Depends(database)):
    require_config()
    row=db.get(MetaOAuthState,digest(state));nonce=request.cookies.get('focus_meta_oauth','')
    if not row or row.consumed or row.expires_at<now() or not hmac.compare_digest(row.nonce_hash,digest(nonce)):raise HTTPException(403,'Nieprawidłowa lub wygasła autoryzacja')
    session=db.get(LoginSession,row.session_hash);user=db.get(User,row.user_id)
    if not session or session.user_id!=row.user_id or session.expires<now() or not user or not user.active:raise HTTPException(403,'Sesja autoryzacji wygasła')
    owner(user)
    code=code.removesuffix('#_')
    try:
        changed=db.execute(update(MetaOAuthState).where(MetaOAuthState.state_hash==row.state_hash,MetaOAuthState.consumed==0).values(consumed=1,code_hash=digest(code) if code and not error and not error_reason else None));db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(403,'Kod autoryzacji został już wykorzystany')
    if changed.rowcount!=1:raise HTTPException(403,'Autoryzacja wykorzystana')
    response.delete_cookie('focus_meta_oauth',path='/api/meta/oauth/callback',secure=True,httponly=True,samesite='lax')
    if error or error_reason or not code:return {'connected':False,'reason':'authorization_cancelled'}
    code=code.removesuffix('#_')
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client:
            r=client.get(GRAPH+'/oauth/access_token',params={'client_id':os.environ['META_APP_ID'],'client_secret':os.environ['META_APP_SECRET'],'redirect_uri':os.environ['META_REDIRECT_URI'],'code':code});r.raise_for_status();token=r.json()['access_token']
            debug=validate_token(client,token)
            r=client.get(GRAPH+'/me',params={'fields':'client_business_id'},headers=graph_headers(token));r.raise_for_status();business=r.json()
            r=client.get(GRAPH+'/me/assigned_instagram_accounts',params={'fields':'id,username'},headers=graph_headers(token));r.raise_for_status()
            account=next(a for a in r.json()['data'] if str(a['id'])==os.environ['META_TEST_ACCOUNT_ID'])
            if account['username'].casefold()==TARGET_USERNAME:raise ValueError('Only distinct test accounts are allowed')
        account_id=str(account['id']);stored=db.get(MetaCredential,account_id)
        if not stored:stored=MetaCredential(account_id=account_id);db.add(stored)
        stored.business_id=str(business['client_business_id']);stored.subject_id=str(debug.get('user_id') or business['id']);stored.username=account['username'];stored.config_id=os.environ['META_CONFIG_ID'];stored.token_ciphertext=seal('token',token);stored.revoked=0;stored.checked_at=now()
        expiry=int(debug.get('expires_at',0));stored.expires_at=datetime.fromtimestamp(expiry,timezone.utc).isoformat() if expiry else ''
        db.commit();request.state.audit_user_id=user.id
        return {'connected':True,'test_account_verified':True,'credential_storage':'encrypted_postgresql','outbound':False}
    except Exception:
        db.rollback();raise HTTPException(502,'Autoryzacja Meta nie powiodła się; sprawdź konfigurację Unified Login i konto testowe')

@router.post('/refresh')
def refresh(user=Depends(manager),db=Depends(database)):
    require_config();owner(user);row=credentials(db)
    if not row:raise HTTPException(409,'Wymagana ponowna autoryzacja')
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client:debug=validate_token(client,unseal('token',row.token_ciphertext))
        expiry=int(debug.get('expires_at',0));row.expires_at=datetime.fromtimestamp(expiry,timezone.utc).isoformat() if expiry else '';row.checked_at=now();db.commit()
        return {'validated':True,'rotated':False,'reauthorize_before_expiry':bool(expiry),'note':'SUAT nie używa ig_refresh_token; bez business_management stosujemy ponowny OAuth przed wygaśnięciem.'}
    except Exception:
        row.revoked=1;row.token_ciphertext='';db.commit()
        raise HTTPException(502,'Token nieaktywny; połączenie lokalnie wyłączone, wymagana autoryzacja')

@router.post('/disconnect')
def disconnect(user=Depends(manager),db=Depends(database)):
    owner(user)
    for row in db.scalars(select(MetaCredential)):row.revoked=1;row.token_ciphertext=''
    db.execute(delete(MetaOAuthState));db.commit()
    return {'connected':False,'provider_revocation_required':True,'note':'Usuń również uprawnienie aplikacji w oficjalnych ustawieniach integracji biznesowych Meta.'}

@router.get('/webhook')
def verify_webhook(request:Request):
    require_config();q=request.query_params
    if q.get('hub.mode')!='subscribe' or not hmac.compare_digest(q.get('hub.verify_token',''),os.environ['META_VERIFY_TOKEN']):raise HTTPException(403,'Nieprawidłowa weryfikacja webhooka')
    challenge=q.get('hub.challenge','')
    if not challenge or len(challenge)>200:raise HTTPException(400,'Nieprawidłowe wyzwanie')
    return Response(challenge,media_type='text/plain')

@router.post('/webhook')
async def webhook(request:Request,db=Depends(database)):
    require_config();raw=await request.body()
    expected='sha256='+hmac.new(os.environ['META_APP_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get('X-Hub-Signature-256',''),expected):raise HTTPException(403,'Nieprawidłowy podpis webhooka')
    try:payload=json.loads(raw)
    except (ValueError,UnicodeDecodeError):raise HTTPException(400,'Nieprawidłowy JSON')
    if not isinstance(payload,dict) or payload.get('object')!='instagram' or not isinstance(payload.get('entry'),list):raise HTTPException(400,'Nieprawidłowy webhook')
    # All processing is one transaction; a retried batch cannot duplicate CRM activities.
    try:
        for entry in payload['entry']:
            if not isinstance(entry,dict) or str(entry.get('id',''))!=os.environ['META_TEST_ACCOUNT_ID']:continue
            grant=db.scalar(select(MetaCredential).where(MetaCredential.account_id==os.environ['META_TEST_ACCOUNT_ID']).with_for_update())
            if grant and grant.revoked:continue
            events=entry.get('messaging',[])
            if not isinstance(events,list):continue
            for event in events:
                if not isinstance(event,dict):continue
                message=event.get('message',{})
                if not isinstance(message,dict):continue
                mid=message.get('mid')
                if not isinstance(mid,str) or not 0<len(mid)<=250:continue
                sender=str(event.get('sender',{}).get('id',''));recipient=str(event.get('recipient',{}).get('id',''))
                account=os.environ['META_TEST_ACCOUNT_ID'];echo=sender==account and message.get('is_echo') is True
                if not echo and recipient!=account:continue
                peer=recipient if echo else sender
                if not peer or peer==account or len(peer)>100:continue
                try:at=datetime.fromtimestamp(int(event['timestamp'])/1000,timezone.utc)
                except (KeyError,ValueError,TypeError,OverflowError,OSError):continue
                if at>datetime.now(timezone.utc)+timedelta(minutes=5) or at<datetime.now(timezone.utc)-timedelta(days=90):continue
                c=db.scalar(select(MetaConversation).where(MetaConversation.account_id==account,MetaConversation.peer_id==peer).with_for_update())
                if not c:
                    try:
                        with db.begin_nested():
                            c=MetaConversation(id=uid(),account_id=account,peer_id=peer);db.add(c);db.flush()
                    except IntegrityError:c=db.scalar(select(MetaConversation).where(MetaConversation.account_id==account,MetaConversation.peer_id==peer).with_for_update())
                existing=db.scalar(select(MetaMessage).where(MetaMessage.conversation_id==c.id,MetaMessage.external_id==mid))
                if existing:
                    if message.get('is_deleted') and existing.status!='deleted':existing.body_ciphertext='';existing.status='deleted'
                    continue
                deleted=bool(message.get('is_deleted'));text=message.get('text','')
                if not isinstance(text,str):text=''
                text=text[:10000]
                item=MetaMessage(id=uid(),conversation_id=c.id,external_id=mid,status='deleted' if deleted else 'api_confirmed_sent' if echo else 'received',direction='outbound' if echo else 'inbound',body_ciphertext=seal('message',text) if text and not deleted and at>datetime.now(timezone.utc)-timedelta(days=30) else '',occurred_at=at.isoformat())
                try:
                    with db.begin_nested():db.add(item);db.flush()
                except IntegrityError:continue
                if not echo and not deleted:
                    c.last_inbound_at=max(c.last_inbound_at or '',at.isoformat())
                    if opt_out(text):c.opted_out=1
                if c.salon_id:
                    salon=db.get(Salon,c.salon_id)
                    audit(db,c,salon.owner_id,'instagram_deleted' if deleted else 'instagram_received' if not echo else 'instagram_sent','Webhook Meta potwierdził zdarzenie; źródło meta_message:'+item.id)
        db.commit()
    except Exception:
        db.rollback();raise HTTPException(503,'Zapis zdarzeń chwilowo niedostępny; ponów webhook')
    return {'accepted':True}

@router.get('/conversations')
def conversations(user=Depends(current),db=Depends(database)):
    require_config();stmt=select(MetaConversation)
    if user.role!='manager':stmt=stmt.join(Salon).where(Salon.owner_id==user.id)
    return [{'id':c.id,'salon_id':c.salon_id,'last_inbound_at':c.last_inbound_at,'opted_out':bool(c.opted_out),'standard_window_open':bool(c.last_inbound_at and c.last_inbound_at>(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat()),'outbound':False} for c in db.scalars(stmt.order_by(MetaConversation.created_at.desc()).limit(100))]

class BindIn(BaseModel):salon_id:str
@router.post('/conversations/{id}/bind')
def bind(id:str,payload:BindIn,user=Depends(manager),db=Depends(database)):
    require_config();c=conversation_access(db,id,user,lock=True);salon=db.get(Salon,payload.salon_id)
    if not salon:raise HTTPException(404,'Salon niedostępny')
    if c.salon_id and c.salon_id!=salon.id:raise HTTPException(409,'Konwersacja już powiązana; wymagana osobna procedura korekty')
    if not c.salon_id:
        c.salon_id=salon.id;audit(db,c,user.id,'instagram_link','Ręcznie potwierdzono powiązanie konwersacji Instagram z salonem')
        for m in db.scalars(select(MetaMessage).where(MetaMessage.conversation_id==c.id,MetaMessage.status=='received')):
            db.add(Activity(id=uid(),salon_id=salon.id,user_id=user.id,kind='instagram_received',body='Powiązano odpowiedź Meta; źródło meta_message:'+m.id,created_at=m.occurred_at))
    db.commit();return {'linked':True}

@router.get('/conversations/{id}/messages')
def messages(id:str,user=Depends(current),db=Depends(database)):
    require_config();conversation_access(db,id,user)
    return [public_message(m) for m in db.scalars(select(MetaMessage).where(MetaMessage.conversation_id==id).order_by(MetaMessage.occurred_at.desc()).limit(100))]

class DraftIn(BaseModel):text:str=Field(min_length=1,max_length=1000)
@router.post('/conversations/{id}/drafts',status_code=201)
def draft(id:str,payload:DraftIn,user=Depends(current),db=Depends(database)):
    require_config();c=conversation_access(db,id,user,lock=True)
    if not c.salon_id:raise HTTPException(409,'Najpierw powiąż salon')
    salon=db.get(Salon,c.salon_id)
    if c.opted_out or salon.status=='do_not_contact':raise HTTPException(409,'Kontakt zablokowany')
    if len(payload.text.encode())>1000:raise HTTPException(422,'Limit tekstu Meta: 1000 bajtów')
    item=MetaMessage(id=uid(),conversation_id=c.id,status='draft',direction='outbound',body_ciphertext=seal('message',payload.text),occurred_at=now());db.add(item)
    audit(db,c,user.id,'instagram_draft','Zapisano szkic Instagram; nie wysłano');db.commit();return public_message(item)

@router.post('/messages/{id}/approve')
def approve(id:str,user=Depends(manager),db=Depends(database)):
    require_config();owner(user);conversation_id=db.scalar(select(MetaMessage.conversation_id).where(MetaMessage.id==id))
    if not conversation_id:raise HTTPException(404)
    c=conversation_access(db,conversation_id,user,lock=True)
    m=db.scalar(select(MetaMessage).where(MetaMessage.id==id).with_for_update());salon=db.get(Salon,c.salon_id) if c.salon_id else None
    if c.opted_out or not salon or salon.status=='do_not_contact':raise HTTPException(409,'Kontakt zablokowany')
    if m.status!='draft' or not m.body_ciphertext or m.occurred_at<(datetime.now(timezone.utc)-timedelta(days=30)).isoformat():raise HTTPException(409,'Wymagany aktualny szkic')
    m.status='approved';m.approved_by=user.id;audit(db,c,user.id,'instagram_approved','Właściciel zatwierdził szkic; nie wysłano');db.commit();return public_message(m)

@router.post('/messages/{id}/manual-sent')
def manual_sent(id:str,user=Depends(manager),db=Depends(database)):
    require_config();owner(user);conversation_id=db.scalar(select(MetaMessage.conversation_id).where(MetaMessage.id==id))
    if not conversation_id:raise HTTPException(404)
    c=conversation_access(db,conversation_id,user,lock=True)
    m=db.scalar(select(MetaMessage).where(MetaMessage.id==id).with_for_update())
    if m.status!='approved' or not m.body_ciphertext or m.occurred_at<(datetime.now(timezone.utc)-timedelta(days=30)).isoformat():raise HTTPException(409,'Najpierw zatwierdź aktualny szkic')
    if c.opted_out or db.get(Salon,c.salon_id).status=='do_not_contact':raise HTTPException(409,'Kontakt zablokowany')
    m.status='manual_sent';audit(db,c,user.id,'instagram_manual','Właściciel oświadczył wysłanie ręczne; brak potwierdzenia dostarczenia z API');db.commit();return public_message(m)

def expire_content(db,at=None):
    at=at or datetime.now(timezone.utc)
    # Preserve minimal message IDs for 90 days, but not content older than 30 days.
    db.execute(update(MetaMessage).where(MetaMessage.occurred_at<(at-timedelta(days=30)).isoformat()).values(body_ciphertext=''))
    db.execute(delete(MetaMessage).where(MetaMessage.occurred_at<(at-timedelta(days=90)).isoformat()))
    db.execute(delete(MetaOAuthState).where(MetaOAuthState.expires_at<at.isoformat()));db.commit()

def agent_replies(db,salon_id):
    if not enabled():return []
    items=db.scalars(select(MetaMessage).join(MetaConversation).where(MetaConversation.salon_id==salon_id,MetaMessage.status=='received',MetaMessage.body_ciphertext!='').order_by(MetaMessage.occurred_at.desc()).limit(15))
    return [SimpleNamespace(id='meta_message:'+m.id,kind='instagram_received',created_at=m.occurred_at,body=unseal('message',m.body_ciphertext)) for m in items if m.occurred_at>(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()]

@router.post('/subscribe')
def subscribe(user=Depends(manager),db=Depends(database)):
    require_config();owner(user);token=credentials(db)
    if not token:raise HTTPException(409,'Wymagane autoryzowane konto testowe')
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client:
            response=client.post(GRAPH+'/'+token.account_id+'/subscribed_apps',headers={'Authorization':'Bearer '+unseal('token',token.token_ciphertext)},data={'subscribed_fields':'messages'})
            response.raise_for_status()
            if response.json().get('success') is not True:raise ValueError()
        return {'subscribed':True,'fields':['messages'],'outbound':False}
    except Exception:raise HTTPException(502,'Subskrypcja nie została potwierdzona przez Meta')

# These signed privacy callbacks stay available when the feature flag is off.
# They do not accept a CRM cookie as authorization and never return customer data.
def signed_request_data(value):
    import base64
    secret=os.getenv('META_APP_SECRET','')
    if not secret:raise HTTPException(503,'Callback wymaga konfiguracji aplikacji Meta')
    try:
        signature,encoded=value.split('.',1)
        decode=lambda s:base64.urlsafe_b64decode(s+'='*((-len(s))%4))
        expected=hmac.new(secret.encode(),encoded.encode(),hashlib.sha256).digest()
        if not hmac.compare_digest(decode(signature),expected):raise ValueError()
        data=json.loads(decode(encoded))
        if data.get('algorithm','').upper()!='HMAC-SHA256' or not isinstance(data.get('user_id'),str) or not 0<len(data['user_id'])<=100:raise ValueError()
        if data.get('issued_at') and abs(datetime.now(timezone.utc).timestamp()-int(data['issued_at']))>86400:raise ValueError()
        return data
    except Exception:raise HTTPException(403,'Nieprawidłowe podpisane żądanie Meta')

async def privacy_callback(kind,request,db):
    data=signed_request_data((await request.form()).get('signed_request',''))
    request_hash=digest(kind+':'+str(data.get('issued_at',''))+':'+data['user_id'])
    existing=db.scalar(select(MetaPrivacyRequest).where(MetaPrivacyRequest.request_hash==request_hash))
    if existing:return existing
    rows=list(db.scalars(select(MetaCredential).where(MetaCredential.subject_id==data['user_id']).with_for_update()))
    for row in rows:
        row.token_ciphertext='';row.revoked=1
        if kind=='deletion':
            conversation_ids=select(MetaConversation.id).where(MetaConversation.account_id==row.account_id)
            db.execute(update(MetaMessage).where(MetaMessage.conversation_id.in_(conversation_ids)).values(body_ciphertext=''))
            row.username='';row.business_id='';row.subject_id='erased:'+digest(row.subject_id)
            row.expires_at=''
    item=MetaPrivacyRequest(id=uid(),request_hash=request_hash,subject_hash=hmac.new(os.environ['META_APP_SECRET'].encode(),data['user_id'].encode(),hashlib.sha256).hexdigest(),kind=kind,status=('content_erased_review_pending' if kind=='deletion' else 'disconnected_review_pending') if rows else 'pending_identity_review')
    try:
        with db.begin_nested():db.add(item);db.flush()
    except IntegrityError:item=db.scalar(select(MetaPrivacyRequest).where(MetaPrivacyRequest.request_hash==request_hash))
    db.commit();return item

@router.post('/deauthorize')
async def deauthorize(request:Request,db=Depends(database)):
    await privacy_callback('deauthorize',request,db);return {'accepted':True}

@router.post('/data-deletion')
async def data_deletion(request:Request,db=Depends(database)):
    item=await privacy_callback('deletion',request,db)
    origin=os.getenv('APP_ORIGIN','https://ai-focus-3-0.onrender.com').rstrip('/')
    return {'url':origin+'/api/meta/data-deletion/status/'+item.id,'confirmation_code':item.id}

@router.get('/data-deletion/status/{id}')
def deletion_status(id:str,db=Depends(database)):
    item=db.get(MetaPrivacyRequest,id)
    if not item or item.kind!='deletion':raise HTTPException(404)
    return {'status':item.status,'scope':'Meta integration credentials and conversation content; broader CRM requests require administrator review'}

@router.get('/privacy',include_in_schema=False)
def privacy_policy():
    controller=os.getenv('PRIVACY_CONTROLLER_NAME','Nazwa administratora wymaga uzupełnienia przez właściciela przed App Review')
    contact=os.getenv('PRIVACY_CONTACT_EMAIL','Kontakt z administratorem: przez właściciela konta Ai Focus')
    return Response('Ai Focus 3.0 — polityka integracji testowej Meta\nAdministrator: '+controller+'\nKontakt: '+contact+'\nCel: obsługa autoryzowanego konta testowego i zapis zdarzeń Instagram w CRM. Bez automatycznej wysyłki.\nZakres: identyfikatory kont i wiadomości, treść rozmów, uprawnienia i zaszyfrowany token. Dane nie są sprzedawane ani używane do treningu modeli.\nPrzetwarzanie wymaga ustalenia podstawy prawnej przez administratora; publiczny profil nie stanowi zgody marketingowej.\nTreści rozmów: maksymalnie 30 dni; minimalne identyfikatory zdarzeń: 90 dni. Kopie i odrębne rekordy CRM podlegają polityce administratora.\nProcesor hostingu: Render, region Frankfurt; dostawca platformy: Meta. Przed uruchomieniem kont rzeczywistych administrator weryfikuje DPA i transfery danych.\nPrawa: dostęp, sprostowanie, usunięcie, ograniczenie, sprzeciw i skarga do UODO — kontakt powyżej.\nOdłączenie w ustawieniach CRM usuwa lokalny token. Uprawnienia można odwołać również w ustawieniach integracji biznesowych Meta.\nŻądania usunięcia Meta są weryfikowane podpisem; niejednoznaczną tożsamość administrator weryfikuje ręcznie.\nTo dokument wdrożenia testowego, wymagający zatwierdzenia i uzupełnienia tożsamości administratora przed App Review.\n',media_type='text/plain')

def maintain_credentials(db):
    """Daily validity check; no broad business_management permission or send API."""
    if not enabled():return
    require_config()
    for row in db.scalars(select(MetaCredential).where(MetaCredential.revoked==0).with_for_update(skip_locked=True)):
        if row.expires_at and row.expires_at<=now():row.revoked=1;row.token_ciphertext='';continue
        if row.checked_at>(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat():continue
        try:
            with httpx.Client(timeout=20,follow_redirects=False) as client:validate_token(client,unseal('token',row.token_ciphertext))
            row.checked_at=now()
        except InvalidMetaGrant:
            row.revoked=1;row.token_ciphertext=''
        except httpx.HTTPStatusError as error:
            if error.response.status_code in (400,401,403):row.revoked=1;row.token_ciphertext=''
        except Exception:logging.getLogger('meta').warning('Meta credential check deferred; no customer action performed')
    db.commit()
