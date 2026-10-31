"""Only synthetic events and mocked Meta transport. No actual messages or accounts."""
import os,json,hmac,hashlib,base64
from datetime import datetime,timedelta,timezone
from urllib.parse import urlsplit,parse_qs
import pytest,httpx
from cryptography.fernet import Fernet
from sqlalchemy import select
from tests.test_api import clean,client,add
from backend.db import Session,Activity
from backend.meta_models import MetaCredential,MetaMessage,MetaOAuthState
from backend.meta import seal,unseal,credentials,expire_content

@pytest.fixture(autouse=True)
def configure(monkeypatch):
    for k,v in {'META_ENABLED':'true','META_MODE':'development','META_APP_ID':'123456','META_APP_SECRET':'synthetic-secret','META_CONFIG_ID':'synthetic-config','META_VERIFY_TOKEN':'synthetic-verify','META_ENCRYPTION_KEY':Fernet.generate_key().decode(),'META_TEST_ACCOUNT_ID':'90001','META_REDIRECT_URI':'https://testserver/api/meta/oauth/callback','BOOTSTRAP_EMAIL':'manager@focus.test'}.items():monkeypatch.setenv(k,v)

def event(mid='test-mid',text='Proszę o termin wizyty',**kw):
    return {'object':'instagram','entry':[{'id':'90001','messaging':[{'sender':{'id':'90002'},'recipient':{'id':'90001'},'timestamp':int(datetime.now(timezone.utc).timestamp()*1000),'message':{'mid':mid,'text':text,**kw}}]}]}
def webhook(c,data,valid=True):
    body=json.dumps(data,ensure_ascii=False).encode();signature='sha256='+hmac.new(b'synthetic-secret',body,hashlib.sha256).hexdigest()
    return c.post('/api/meta/webhook',content=body,headers={'Content-Type':'application/json','X-Hub-Signature-256':signature if valid else 'sha256=invalid'})
def cid(c):return c.get('/api/meta/conversations').json()[0]['id']

def test_disabled_mode_and_webhook_verification(monkeypatch):
    c=client();monkeypatch.setenv('META_ENABLED','false')
    assert c.get('/api/meta/status').json()['outbound'] is False
    assert webhook(c,event()).status_code==404
    monkeypatch.setenv('META_ENABLED','true');monkeypatch.setenv('META_MODE','live')
    assert c.post('/api/meta/oauth/start').status_code==409
    monkeypatch.setenv('META_MODE','development')
    assert c.get('/api/meta/webhook',params={'hub.mode':'subscribe','hub.verify_token':'synthetic-verify','hub.challenge':'123'}).text=='123'
    assert c.get('/api/meta/webhook',params={'hub.mode':'subscribe','hub.verify_token':'wrong','hub.challenge':'123'}).status_code==403
    assert webhook(c,event(),False).status_code==403

def test_idempotency_encrypted_content_crm_link_and_deletion():
    c=client();s=add(c);assert webhook(c,event()).status_code==200
    conversation=cid(c)
    assert c.post('/api/meta/conversations/'+conversation+'/bind',json={'salon_id':s['id']}).status_code==200
    assert webhook(c,event()).status_code==200
    with Session() as db:
        rows=list(db.scalars(select(MetaMessage)));assert len(rows)==1
        assert 'Proszę' not in rows[0].body_ciphertext and unseal('message',rows[0].body_ciphertext)=='Proszę o termin wizyty'
        assert len(list(db.scalars(select(Activity).where(Activity.kind=='instagram_received'))))==1
    webhook(c,event(is_deleted=True));webhook(c,event())
    messages=c.get('/api/meta/conversations/'+conversation+'/messages').json()
    assert len(messages)==1 and messages[0]['status']=='deleted' and messages[0]['text']==''

def test_roles_approval_manual_status_and_no_send_route():
    owner=client();rep=client('rep1');other=client('rep2');s=add(rep);webhook(owner,event());conversation=cid(owner)
    owner.post('/api/meta/conversations/'+conversation+'/bind',json={'salon_id':s['id']})
    assert other.get('/api/meta/conversations/'+conversation+'/messages').status_code==404
    r=rep.post('/api/meta/conversations/'+conversation+'/drafts',json={'text':'Czy możemy umówić wizytę 15–20 minut?'});assert r.status_code==201
    mid=r.json()['id'];assert r.json()['status']=='draft'
    assert rep.post('/api/meta/messages/'+mid+'/approve').status_code==403
    assert owner.post('/api/meta/messages/'+mid+'/manual-sent').status_code==409
    assert owner.post('/api/meta/messages/'+mid+'/approve').json()['status']=='approved'
    assert owner.post('/api/meta/messages/'+mid+'/manual-sent').json()['status']=='manual_sent'
    assert owner.post('/api/meta/messages/'+mid+'/manual-sent').status_code==409
    assert owner.post('/api/meta/messages/'+mid+'/send').status_code in (404,405)
    assert rep.post('/api/meta/conversations/'+conversation+'/drafts',json={'text':'ą'*600}).status_code==422
    webhook(owner,event('stop-mid','Nie kontaktuj się ponownie'))
    assert rep.post('/api/meta/conversations/'+conversation+'/drafts',json={'text':'Szkic'}).status_code==409

def test_window_retention_and_no_replay_of_old_events():
    c=client();data=event();data['entry'][0]['messaging'][0]['timestamp']=int((datetime.now(timezone.utc)-timedelta(hours=25)).timestamp()*1000)
    webhook(c,data);conversation=cid(c)
    assert not c.get('/api/meta/conversations').json()[0]['standard_window_open']
    with Session() as db:
        m=db.scalar(select(MetaMessage));m.occurred_at=(datetime.now(timezone.utc)-timedelta(days=31)).isoformat();db.commit();expire_content(db)
        assert db.get(MetaMessage,m.id).body_ciphertext==''
        m.occurred_at=(datetime.now(timezone.utc)-timedelta(days=91)).isoformat();db.commit();expire_content(db)
        assert not list(db.scalars(select(MetaMessage)))
    data['entry'][0]['messaging'][0]['timestamp']=int((datetime.now(timezone.utc)-timedelta(days=91)).timestamp()*1000);webhook(c,data)
    assert not c.get('/api/meta/conversations/'+conversation+'/messages').json()

class FakeMeta:
    wrong_scope=False;wrong_account=False;target=False;fail=False;extra_scope=False;codes=[]
    def __init__(self,**kw):assert kw['follow_redirects'] is False
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def get(self,url,**kw):
        assert url.startswith('https://graph.facebook.com/v26.0/')
        if url.endswith('/oauth/access_token'):
            self.codes.append(kw['params']['code']);data={'access_token':'synthetic-token'}
        elif url.endswith('/debug_token'):data={'data':{'app_id':'123456','is_valid':not self.fail,'type':'SYSTEM_USER','user_id':'subject-test','scopes':[] if self.wrong_scope else ['instagram_basic','instagram_manage_messages']+(['business_management'] if self.extra_scope else []),'expires_at':0}}
        elif url.endswith('/me'):data={'client_business_id':'business-test','id':'subject-test'}
        elif url.endswith('/me/assigned_instagram_accounts'):data={'data':[{'id':'90003' if self.wrong_account else '90001','username':'artur_uluru_hair' if self.target else 'synthetic_professional'}]}
        else:raise AssertionError(url)
        return httpx.Response(200,json=data,request=httpx.Request('GET',url))
    def post(self,url,**kw):
        assert url.endswith('/90001/subscribed_apps');return httpx.Response(200,json={'success':True},request=httpx.Request('POST',url))

def authorize(c,monkeypatch,fake=FakeMeta,error=False):
    c.base_url='https://testserver';r=c.post('/api/meta/oauth/start');assert r.status_code==200
    query=parse_qs(urlsplit(r.json()['authorization_url']).query);assert query['config_id']==['synthetic-config'] and 'scope' not in query
    monkeypatch.setattr(httpx,'Client',fake)
    params={'state':query['state'][0],'code':'synthetic-code#_'}
    if error:params.update(error='access_denied',error_reason='user_denied')
    return c.get('/api/meta/oauth/callback',params=params),query['state'][0]

def test_unified_oauth_encrypted_db_replay_and_disconnect(monkeypatch,caplog):
    c=client();r,state=authorize(c,monkeypatch)
    assert r.status_code==200,r.text
    assert r.json()['connected'] and 'synthetic-token' not in r.text and FakeMeta.codes[-1]=='synthetic-code'
    with Session() as db:
        row=credentials(db);assert row.business_id=='business-test' and row.config_id=='synthetic-config'
        assert 'synthetic-token' not in row.token_ciphertext and unseal('token',row.token_ciphertext)=='synthetic-token'
    assert c.get('/api/meta/oauth/callback',params={'state':state,'code':'again'}).status_code==403
    assert c.post('/api/meta/refresh').json()['rotated'] is False
    assert c.post('/api/meta/subscribe').json()['subscribed']
    assert 'synthetic-secret' not in caplog.text and 'synthetic-token' not in caplog.text
    assert c.post('/api/meta/disconnect').json()['connected'] is False
    with Session() as db:assert credentials(db) is None
    assert webhook(c,event()).status_code==200 and c.get('/api/meta/conversations').json()==[]

@pytest.mark.parametrize('failure',['wrong_scope','wrong_account','target','fail','extra_scope'])
def test_oauth_rejects_invalid_grant_and_actual_target(monkeypatch,failure):
    class Reject(FakeMeta):pass
    setattr(Reject,failure,True)
    c=client();r,_=authorize(c,monkeypatch,Reject);assert r.status_code==502
    with Session() as db:assert not list(db.scalars(select(MetaCredential)))

def test_oauth_cancel_expired_state_and_session_binding(monkeypatch):
    c=client();r,state=authorize(c,monkeypatch,error=True);assert not r.json()['connected']
    assert c.get('/api/meta/oauth/callback',params={'state':state,'code':'again'}).status_code==403
    r=c.post('/api/meta/oauth/start');state=parse_qs(urlsplit(r.json()['authorization_url']).query)['state'][0]
    with Session() as db:
        row=db.get(MetaOAuthState,hashlib.sha256(state.encode()).hexdigest());row.expires_at='2000-01-01';db.commit()
    assert c.get('/api/meta/oauth/callback',params={'state':state,'code':'again'}).status_code==403

def signed(user='subject-test'):
    data={'algorithm':'HMAC-SHA256','user_id':user,'issued_at':int(datetime.now(timezone.utc).timestamp())}
    b64=lambda b:base64.urlsafe_b64encode(b).rstrip(b'=')
    payload=b64(json.dumps(data).encode());signature=b64(hmac.new(b'synthetic-secret',payload,hashlib.sha256).digest())
    return (signature+b'.'+payload).decode()

def test_privacy_callbacks_signed_idempotent_and_not_false_completion(monkeypatch):
    c=client();authorize(c,monkeypatch)
    assert c.post('/api/meta/data-deletion',data={'signed_request':'invalid'}).status_code==403
    notification=signed()
    r=c.post('/api/meta/data-deletion',data={'signed_request':notification});assert r.status_code==200
    assert 'synthetic-token' not in r.text
    assert c.get(r.json()['url'].replace('https://ai-focus-3-0.onrender.com','')).json()['status']=='content_erased_review_pending'
    r2=c.post('/api/meta/data-deletion',data={'signed_request':notification});assert r2.json()==r.json()
    with Session() as db:assert not db.get(MetaCredential,'90001').token_ciphertext
    unknown=c.post('/api/meta/data-deletion',data={'signed_request':signed('unknown-person')})
    assert c.get(unknown.json()['url'].replace('https://ai-focus-3-0.onrender.com','')).json()['status']=='pending_identity_review'
    assert c.post('/api/meta/deauthorize',data={'signed_request':signed()}).status_code==200

def test_confirmed_reply_is_used_by_agent_without_sending(monkeypatch):
    from backend.worker import run_once
    monkeypatch.setenv('AGENT_V2_ENABLED','true');monkeypatch.setenv('AI_PAID_PROCESSING_APPROVED','false')
    c=client();s=add(c,specialization='Koloryzacja');webhook(c,event());conversation=cid(c)
    c.post('/api/meta/conversations/'+conversation+'/bind',json={'salon_id':s['id']})
    c.post('/api/agent/jobs',json={'salon_id':s['id']});assert run_once()
    result=json.loads(c.get('/api/agent/jobs').json()[0]['result'])
    assert any('meta_message:' in r['source'] for r in result['reply_reviews'])
    assert '15–20' in result['draft'] and 'NAK' in result['draft'] and 'muk' in result['draft']
    assert not result['sent'] and not result['appointment_created']

def test_nonce_and_logged_out_session_cannot_finish_oauth(monkeypatch):
    c=client();c.base_url='https://testserver'
    r=c.post('/api/meta/oauth/start');state=parse_qs(urlsplit(r.json()['authorization_url']).query)['state'][0]
    other=client();other.base_url='https://testserver'
    assert other.get('/api/meta/oauth/callback',params={'state':state,'code':'synthetic'}).status_code==403
    assert c.post('/api/auth/logout').status_code==200
    assert c.get('/api/meta/oauth/callback',params={'state':state,'code':'synthetic'}).status_code==403

def test_same_code_cannot_be_exchanged_twice_with_new_state(monkeypatch):
    c=client();r,_=authorize(c,monkeypatch);assert r.status_code==200
    r,_=authorize(c,monkeypatch);assert r.status_code==403

def test_daily_check_disables_revoked_token_and_content_retention(monkeypatch):
    from backend.meta import maintain_credentials
    c=client();authorize(c,monkeypatch)
    class Revoked(FakeMeta):fail=True
    monkeypatch.setattr(httpx,'Client',Revoked)
    with Session() as db:
        row=db.get(MetaCredential,'90001');row.checked_at=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat();db.commit()
        maintain_credentials(db);assert row.revoked and not row.token_ciphertext

def test_wrong_encryption_key_never_exposes_token_or_breaks_crm(monkeypatch):
    c=client();r,_=authorize(c,monkeypatch);assert r.status_code==200
    monkeypatch.setenv('META_ENCRYPTION_KEY',Fernet.generate_key().decode())
    r=c.get('/api/meta/status');assert r.status_code==503 and 'synthetic-token' not in r.text
    assert c.get('/api/integrations').status_code==200 and c.get('/api/integrations').json()['instagram']['mode']=='needs_configuration'
    assert c.get('/api/salons').status_code==200
