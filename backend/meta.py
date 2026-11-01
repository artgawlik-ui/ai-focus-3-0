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
from backend.meta_flags import legacy_enabled,feature
from backend.meta_models import MetaWebhookInbox,MetaRefreshState
uid=lambda:str(uuid.uuid4())
# Official exchange/refresh endpoints require secret-bearing query parameters.
# Never allow httpx INFO logging of those URLs.
from backend.meta_logging import install as install_provider_log_guard
install_provider_log_guard()

def enabled():return legacy_enabled()
def require_config(module='crm_history'):
    if not feature(module):raise HTTPException(404,'Moduł Meta wyłączony')
    if os.getenv('META_MODE')!='development':raise HTTPException(409,'Dozwolony wyłącznie tryb deweloperski')
    required={
        'oauth':('META_APP_ID','META_APP_SECRET','META_CONFIG_ID','META_ENCRYPTION_KEY','META_TEST_ACCOUNT_ID','META_REDIRECT_URI'),
        'webhook_verify':('META_VERIFY_TOKEN',),
        'ingest':('META_APP_SECRET','META_ENCRYPTION_KEY','META_TEST_ACCOUNT_ID'),
        'crm_history':('META_ENCRYPTION_KEY',),
        'diagnostics':('META_ENCRYPTION_KEY','META_TEST_ACCOUNT_ID'),
    }[module]
    # Legacy-only installations keep the original all-config guard unchanged.
    if os.getenv('META_'+module.upper()+'_ENABLED') is None:
        required=('META_APP_ID','META_APP_SECRET','META_CONFIG_ID','META_VERIFY_TOKEN','META_ENCRYPTION_KEY','META_TEST_ACCOUNT_ID','META_REDIRECT_URI')
    if any(not os.getenv(k) for k in required):raise HTTPException(503,'Brak bezpiecznej konfiguracji integracji')
    if 'META_ENCRYPTION_KEY' in required:
        try:Fernet(os.environ['META_ENCRYPTION_KEY'].encode())
        except Exception:raise HTTPException(503,'Nieprawidłowy klucz szyfrowania integracji')
    if 'META_REDIRECT_URI' in required and not os.environ['META_REDIRECT_URI'].startswith('https://'):raise HTTPException(503,'OAuth wymaga HTTPS')

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

def secure_text_equal(left,right):
    # Porównanie bajtów odrzuca nie-ASCII bez wyjątku ujawniającego błąd 500.
    return hmac.compare_digest(left.encode('utf-8'),right.encode('utf-8'))

def graph_headers(token):return {'Authorization':'Bearer '+token}
class InvalidMetaGrant(ValueError):pass
class ConfirmedRevoked(InvalidMetaGrant):pass

def validate_token(client,token):
    r=client.get(GRAPH+'/debug_token',params={'input_token':token},headers=graph_headers(os.environ['META_APP_ID']+'|'+os.environ['META_APP_SECRET']));r.raise_for_status();data=r.json()['data']
    if data.get('is_valid') is False:raise ConfirmedRevoked('Grant invalidated')
    if data.get('is_valid') is not True or str(data.get('app_id'))!=os.environ['META_APP_ID'] or not SCOPES<=set(data.get('scopes',[])) or set(data.get('scopes',[]))-SCOPES-{'public_profile'}:raise InvalidMetaGrant('Invalid grant')
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
    data['modules']={name:feature(name) for name in ('oauth','webhook_verify','ingest','crm_history','diagnostics')}
    if not feature('diagnostics'):return data
    if not data['can_approve']:return data
    require_config('diagnostics');token=credentials(db)
    data.update(connected=bool(token),account_verified=bool(token),expires_at=token.expires_at if token else None,reauthorization_required=not bool(token))
    check=db.get(MetaRefreshState,os.environ['META_TEST_ACCOUNT_ID'])
    data['credential_check']={'status':check.status,'attempts':check.attempts,'retry_at':check.next_attempt_at or None,'error_category':check.last_error or None} if check else {'status':'not_checked'}
    return data

@router.post('/oauth/start')
def oauth_start(request:Request,response:Response,user=Depends(manager),db=Depends(database)):
    require_config('oauth');owner(user)
    if db.scalar(select(func.count()).select_from(MetaOAuthState).where(MetaOAuthState.user_id==user.id,MetaOAuthState.expires_at>now(),MetaOAuthState.consumed==0))>=3:raise HTTPException(429,'Zbyt wiele rozpoczętych autoryzacji')
    state=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32)
    db.execute(delete(MetaOAuthState).where(MetaOAuthState.expires_at<now()))
    db.add(MetaOAuthState(state_hash=digest(state),nonce_hash=digest(nonce),session_hash=digest(request.cookies['focus_session']),user_id=user.id,expires_at=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()));db.commit()
    response.set_cookie('focus_meta_oauth',nonce,httponly=True,secure=True,samesite='lax',max_age=600,path='/api/meta/oauth/callback')
    return {'authorization_url':'https://www.facebook.com/dialog/oauth?'+urlencode({'client_id':os.environ['META_APP_ID'],'config_id':os.environ['META_CONFIG_ID'],'redirect_uri':os.environ['META_REDIRECT_URI'],'response_type':'code','state':state,'prompt':'login'})}

@router.get('/oauth/callback')
def oauth_callback(request:Request,response:Response,state:str='',code:str='',error:str='',error_reason:str='',db=Depends(database)):
    require_config('oauth')
    row=db.get(MetaOAuthState,digest(state));nonce=request.cookies.get('focus_meta_oauth','')
    if not row or row.consumed or row.expires_at<now() or not hmac.compare_digest(row.nonce_hash,digest(nonce)):raise HTTPException(403,'Nieprawidłowa lub wygasła autoryzacja')
    session=db.get(LoginSession,row.session_hash);user=db.get(User,row.user_id)
    if not session or session.user_id!=row.user_id or session.expires<now() or not user or not user.active:raise HTTPException(403,'Sesja autoryzacji wygasła')
    owner(user)
    if not hmac.compare_digest(row.session_hash,digest(request.cookies.get('focus_session',''))):raise HTTPException(403,'Sesja autoryzacji niezgodna')
    code=code.removesuffix('#_')
    try:
        changed=db.execute(update(MetaOAuthState).where(MetaOAuthState.state_hash==row.state_hash,MetaOAuthState.consumed==0).values(consumed=1,code_hash=digest(code) if code and not error and not error_reason else None));db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(403,'Kod autoryzacji został już wykorzystany')
    if changed.rowcount!=1:raise HTTPException(403,'Autoryzacja wykorzystana')
    response.delete_cookie('focus_meta_oauth',path='/api/meta/oauth/callback',secure=True,httponly=True,samesite='lax')
    if error or error_reason or not code:return {'connected':False,'reason':'authorization_cancelled'}
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client:
            r=client.get(GRAPH+'/oauth/access_token',params={'client_id':os.environ['META_APP_ID'],'client_secret':os.environ['META_APP_SECRET'],'redirect_uri':os.environ['META_REDIRECT_URI'],'code':code});r.raise_for_status();token=r.json()['access_token']
            debug=validate_token(client,token)
            r=client.get(GRAPH+'/me',params={'fields':'client_business_id'},headers=graph_headers(token));r.raise_for_status();business=r.json()
            r=client.get(GRAPH+'/me/assigned_instagram_accounts',params={'fields':'id,username'},headers=graph_headers(token));r.raise_for_status()
            account=next(a for a in r.json()['data'] if str(a['id'])==os.environ['META_TEST_ACCOUNT_ID'])
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
    require_config('oauth');owner(user)
    # Release the authentication dependency's transaction before provider I/O.
    db.commit()
    from backend.meta_refresh import check
    result=check(os.environ['META_TEST_ACCOUNT_ID'])
    db.expire_all()
    return result

@router.post('/disconnect')
def disconnect(user=Depends(manager),db=Depends(database)):
    owner(user)
    for row in db.scalars(select(MetaCredential)):row.revoked=1;row.token_ciphertext=''
    db.execute(delete(MetaOAuthState));db.commit()
    return {'connected':False,'provider_revocation_required':True,'note':'Usuń również uprawnienie aplikacji w oficjalnych ustawieniach integracji biznesowych Meta.'}

@router.get('/webhook')
def verify_webhook(request:Request):
    require_config('webhook_verify');q=request.query_params
    if q.get('hub.mode')!='subscribe' or not secure_text_equal(q.get('hub.verify_token',''),os.environ['META_VERIFY_TOKEN']):raise HTTPException(403,'Nieprawidłowa weryfikacja webhooka')
    challenge=q.get('hub.challenge','')
    if not challenge or len(challenge)>200:raise HTTPException(400,'Nieprawidłowe wyzwanie')
    return Response(challenge,media_type='text/plain')

@router.post('/webhook')
async def webhook(request:Request):
    require_config('ingest')
    from backend.meta_inbox import MAX_BODY,MAX_EVENTS,persist
    raw=bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk)>MAX_BODY:raise HTTPException(413,'Webhook przekracza limit')
        raw.extend(chunk)
    expected='sha256='+hmac.new(os.environ['META_APP_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
    if not secure_text_equal(request.headers.get('X-Hub-Signature-256',''),expected):raise HTTPException(403,'Nieprawidłowy podpis webhooka')
    try:payload=json.loads(raw)
    except (ValueError,UnicodeDecodeError):raise HTTPException(400,'Nieprawidłowy JSON')
    if not isinstance(payload,dict) or payload.get('object')!='instagram' or not isinstance(payload.get('entry'),list):raise HTTPException(400,'Nieprawidłowy webhook')
    count=sum(len(e.get('messaging',[])) for e in payload['entry'] if isinstance(e,dict) and isinstance(e.get('messaging'),list))
    if count>MAX_EVENTS:raise HTTPException(413,'Zbyt wiele zdarzeń')
    try:
        # Standard server thread pool only for bounded SQL, never a new worker.
        import anyio
        if not hasattr(request.app.state,'meta_inbox_limiter'):
            request.app.state.meta_inbox_limiter=anyio.CapacityLimiter(4)
        await anyio.to_thread.run_sync(persist,payload,limiter=request.app.state.meta_inbox_limiter)
    except Exception:raise HTTPException(503,'Trwały zapis chwilowo niedostępny; ponów webhook')
    return {'accepted':True}

@router.get('/inbox/diagnostics')
def inbox_diagnostics(user=Depends(manager),db=Depends(database)):
    owner(user);require_config('diagnostics')
    from backend.meta_inbox import diagnostics
    return diagnostics(db)

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
    if not feature('crm_history'):return []
    items=db.scalars(select(MetaMessage).join(MetaConversation).where(MetaConversation.salon_id==salon_id,MetaMessage.status=='received',MetaMessage.body_ciphertext!='').order_by(MetaMessage.occurred_at.desc()).limit(15))
    return [SimpleNamespace(id='meta_message:'+m.id,kind='instagram_received',created_at=m.occurred_at,body=unseal('message',m.body_ciphertext)) for m in items if m.occurred_at>(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()]

@router.post('/subscribe')
def subscribe(user=Depends(manager),db=Depends(database)):
    require_config('ingest');owner(user);token=credentials(db)
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
            db.execute(update(MetaWebhookInbox).where(MetaWebhookInbox.account_id==row.account_id).values(payload_ciphertext='',status='done',processed_at=now(),lease_token='',lease_until=''))
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
    return Response('Ai Focus 3.0 — polityka integracji testowej Meta\nAdministrator: '+controller+'\nKontakt: '+contact+'\nCel: obsługa autoryzowanego konta testowego i zapis zdarzeń Instagram w CRM. Bez automatycznej wysyłki.\nZakres: identyfikatory kont i wiadomości, treść rozmów, uprawnienia i zaszyfrowany token. Dane nie są sprzedawane ani używane do treningu modeli.\nPrzetwarzanie wymaga ustalenia podstawy prawnej przez administratora; publiczny profil nie stanowi zgody marketingowej.\nTreści rozmów: maksymalnie 30 dni; minimalne identyfikatory zdarzeń: 90 dni. Zakończony inbox: zaszyfrowany payload 7 dni, metadane 90 dni. Zdarzenia błędne wymagają przeglądu administratora i osobnej decyzji o usunięciu. Kopie i odrębne rekordy CRM podlegają polityce administratora.\nProcesor hostingu: Render, region Frankfurt; dostawca platformy: Meta. Przed uruchomieniem kont rzeczywistych administrator weryfikuje DPA i transfery danych.\nPrawa: dostęp, sprostowanie, usunięcie, ograniczenie, sprzeciw i skarga do UODO — kontakt powyżej.\nOdłączenie w ustawieniach CRM usuwa lokalny token. Uprawnienia można odwołać również w ustawieniach integracji biznesowych Meta.\nŻądania usunięcia Meta są weryfikowane podpisem; niejednoznaczną tożsamość administrator weryfikuje ręcznie.\nTo dokument wdrożenia testowego, wymagający zatwierdzenia i uzupełnienia tożsamości administratora przed App Review.\n',media_type='text/plain')

def maintain_credentials(db):
    if not feature('oauth'):return
    require_config('oauth');db.commit()
    from backend.meta_refresh import maintain
    maintain();db.expire_all()
