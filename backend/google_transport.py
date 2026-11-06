"""Fixed provider endpoints, secrets only in POST bodies/Authorization. No raw errors."""
import os,json,logging
from datetime import datetime,timedelta,timezone
from urllib.parse import quote
from cryptography.fernet import Fernet
import httpx

SCOPE='https://www.googleapis.com/auth/calendar.app.created'
for name in ('httpx','httpcore'):logging.getLogger(name).setLevel(logging.WARNING)


def flag(name):return os.getenv(name,'false').strip().lower()=='true'
def schema():return flag('GOOGLE_SCHEMA_ENABLED')
def enabled():return schema() and flag('GOOGLE_CALENDAR_ENABLED')
def writable():return enabled() and flag('GOOGLE_CALENDAR_WRITE_ENABLED')

class ProviderError(Exception):
    def __init__(self,code,retry=False):self.code=code;self.retry=retry;super().__init__(code)


def cipher():
    try:return Fernet(os.environ['GOOGLE_ENCRYPTION_KEY'].encode())
    except Exception:raise ProviderError('encryption_configuration') from None

def seal(value):return cipher().encrypt(json.dumps(value,sort_keys=True).encode()).decode()
def unseal(value):
    try:return json.loads(cipher().decrypt(value.encode()))
    except Exception:raise ProviderError('credential_unavailable') from None


def token_post(data):
    if not enabled():raise ProviderError('oauth_disabled')
    try:
        response=httpx.post('https://oauth2.googleapis.com/token',data=data,timeout=10,follow_redirects=False)
        body=response.json()
    except Exception:raise ProviderError('oauth_network',True) from None
    if response.status_code==400 and isinstance(body,dict) and body.get('error')=='invalid_grant':raise ProviderError('reauthorization_required')
    if response.status_code==429 or response.status_code>=500:raise ProviderError('oauth_retry',True)
    if response.status_code!=200 or not isinstance(body,dict):raise ProviderError('oauth_rejected')
    return body


def tokens(body,previous=None):
    try:
        if set(body.get('scope',SCOPE if previous else '').split())!={SCOPE}:raise ValueError()
        access=body['access_token'];refresh=body.get('refresh_token') or (previous or {}).get('refresh_token')
        seconds=int(body['expires_in'])
        if not isinstance(access,str) or not access or not isinstance(refresh,str) or not refresh or not 0<seconds<=86400:raise ValueError()
        return {'access_token':access,'refresh_token':refresh,'expires_at':(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat()}
    except Exception:raise ProviderError('oauth_invalid_response') from None


def refresh(account,force=False):
    value=unseal(account.tokens_ciphertext)
    if not force and datetime.fromisoformat(value['expires_at'])>datetime.now(timezone.utc)+timedelta(seconds=60):return value
    try:
        body=token_post({'grant_type':'refresh_token','refresh_token':value['refresh_token'],'client_id':os.environ['GOOGLE_CLIENT_ID'],'client_secret':os.environ['GOOGLE_CLIENT_SECRET']})
        value=tokens(body,value);account.tokens_ciphertext=seal(value)
        return value
    except ProviderError as error:
        if error.code=='reauthorization_required':
            account.revoked=1;account.tokens_ciphertext='';account.status='reauthorization_required'
        raise


def calendar_request(account,method,path,body=None,etag=None):
    # All private provider reads are tied to explicit sync; writes have an independent switch.
    if not enabled():raise ProviderError('oauth_disabled')
    if method!='GET' and not writable():raise ProviderError('transport_disabled')
    if account.revoked or not account.approved:raise ProviderError('account_disabled')
    if method not in ('GET','POST','PATCH'):raise ProviderError('method_not_allowed')
    if path=='calendars':
        if method!='POST':raise ProviderError('target_not_allowed')
    elif not account.calendar_id or not (path==event_path(account.calendar_id) or path.startswith(event_path(account.calendar_id)+'/')):
        raise ProviderError('target_not_allowed')
    for attempt in range(2):
        value=refresh(account,force=attempt==1)
        headers={'Authorization':'Bearer '+value['access_token']}
        if etag:headers['If-Match']=etag
        try:
            response=httpx.request(method,'https://www.googleapis.com/calendar/v3/'+path,headers=headers,json=body,params={'sendUpdates':'none'} if '/events' in path and method!='GET' else None,timeout=10,follow_redirects=False)
        except Exception:raise ProviderError('provider_network',True) from None
        if response.status_code==401:
            if attempt==0:continue
            account.revoked=1;account.tokens_ciphertext='';account.status='reauthorization_required'
            raise ProviderError('reauthorization_required')
        if response.status_code==412:raise ProviderError('remote_conflict')
        if response.status_code in (404,409,410):return response.status_code,{}
        if response.status_code==429 or response.status_code>=500:raise ProviderError('provider_retry',True)
        if response.status_code==403:
            try:reasons={v.get('reason') for v in response.json().get('error',{}).get('errors',[])}
            except Exception:reasons=set()
            raise ProviderError('provider_forbidden',bool(reasons & {'rateLimitExceeded','userRateLimitExceeded'}))
        if response.status_code not in (200,201):raise ProviderError('provider_rejected')
        try:
            data=response.json()
            if not isinstance(data,dict):raise ValueError()
            return response.status_code,data
        except Exception:raise ProviderError('provider_invalid_response') from None
    raise ProviderError('provider_rejected')


def event_path(calendar,event=None):
    path='calendars/'+quote(calendar,safe='')+'/events'
    return path+'/'+quote(event,safe='') if event else path
