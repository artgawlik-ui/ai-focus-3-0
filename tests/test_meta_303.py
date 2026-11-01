"""Synthetic PostgreSQL concurrency, recovery and fail-closed regression suite."""
import json,os,hmac,hashlib,logging,threading,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from urllib.parse import parse_qs,urlsplit
import pytest,httpx
from fastapi import HTTPException
from sqlalchemy import select,func,text
from tests.test_api import clean,client,add
from tests.test_meta import configure,FakeMeta,authorize,event
from backend.db import Session,User,now
from backend.meta import seal,unseal
from backend.meta_models import MetaWebhookInbox,MetaRefreshState,MetaMessage,MetaCredential,MetaOAuthState
from backend.meta_flags import feature,send_dm,MODULES
from backend.meta_inbox import persist,drain_once,claim_batch,process_claim,diagnostics,maintenance
from backend.meta_refresh import check

def post(c,data=None,raw=None,signature=None):
    raw=raw if raw is not None else json.dumps(data or event()).encode()
    signature=signature if signature is not None else 'sha256='+hmac.new(b'synthetic-secret',raw,hashlib.sha256).hexdigest()
    return c.post('/api/meta/webhook',content=raw,headers={'X-Hub-Signature-256':signature})

def token():
    with Session() as db:return db.get(MetaCredential,'90001').token_ciphertext

def seed_token():
    with Session() as db:
        db.add(MetaCredential(account_id='90001',business_id='fixture',subject_id='fixture',username='fixture',config_id='fixture',token_ciphertext=seal('token','synthetic-token'),expires_at='',checked_at=now()));db.commit()

@pytest.mark.parametrize('legacy',[False,True])
def test_legacy_flags_and_explicit_migration(monkeypatch,legacy):
    monkeypatch.setenv('META_ENABLED',str(legacy))
    for module in MODULES:
        monkeypatch.delenv('META_'+module.upper()+'_ENABLED',raising=False)
        assert feature(module)==legacy
    monkeypatch.setenv('META_OAUTH_ENABLED','true')
    monkeypatch.setenv('META_INGEST_ENABLED','false')
    assert feature('oauth') and not feature('ingest')
    for module in ('crm_history','diagnostics','webhook_verify'):assert feature(module)==legacy
    for value in ('','invalid','1'):
        monkeypatch.setenv('META_OAUTH_ENABLED',value);assert not feature('oauth')

@pytest.mark.parametrize('value',[None,'','invalid','false','1','true'])
def test_transport_boundary_never_sends(monkeypatch,value):
    calls=[]
    def forbidden(*a,**k):calls.append(True);raise AssertionError('DM endpoint forbidden')
    monkeypatch.setattr(httpx,'post',forbidden)
    monkeypatch.setattr(httpx.Client,'post',forbidden)
    for name in ('META_ENABLED',)+tuple('META_'+m.upper()+'_ENABLED' for m in MODULES):monkeypatch.setenv(name,'true')
    if value is None:monkeypatch.delenv('META_DM_TRANSPORT_ENABLED',raising=False)
    else:monkeypatch.setenv('META_DM_TRANSPORT_ENABLED',value)
    with pytest.raises(HTTPException) as raised:send_dm('fixture')
    assert raised.value.status_code==(501 if value=='true' else 403)
    assert not calls


def test_authorized_target_name_allowed_without_weakening_id(monkeypatch):
    class Target(FakeMeta):target=True
    c=client();response,_=authorize(c,monkeypatch,Target)
    assert response.status_code==200 and response.json()['connected']
    with Session() as db:assert db.get(MetaCredential,'90001').username=='artur_uluru_hair'


def test_callback_rejects_changed_owner_and_wrong_session(monkeypatch):
    c=client();c.base_url='https://testserver'
    response=c.post('/api/meta/oauth/start');state=parse_qs(urlsplit(response.json()['authorization_url']).query)['state'][0]
    with Session() as db:
        user=db.get(User,'manager');user.email='different@focus.test';db.commit()
    assert c.get('/api/meta/oauth/callback',params={'state':state,'code':'fixture'}).status_code==403
    assert client('rep1').post('/api/meta/oauth/start').status_code==403


def test_callback_exact_redirect_and_no_wire_logs(monkeypatch,caplog):
    class Inspect(FakeMeta):
        def get(self,url,**kw):
            if url.endswith('/oauth/access_token'):
                assert kw['params']['redirect_uri']==os.environ['META_REDIRECT_URI']
                assert 'client_secret' in kw['params'] and 'code' in kw['params']
            if url.endswith('/debug_token'):assert kw['headers']['Authorization'].startswith('Bearer ')
            logging.getLogger('httpx').warning('provider URL hidden %s',url+'?client_secret=fixture-sensitive')
            return super().get(url,**kw)
    c=client();r,_=authorize(c,monkeypatch,Inspect);assert r.status_code==200
    assert 'fixture-sensitive' not in caplog.text
    assert 'synthetic-token' not in caplog.text and 'synthetic-code' not in caplog.text


def test_ack_only_after_commit_and_without_crm(monkeypatch):
    c=client()
    monkeypatch.setattr('backend.meta_inbox.apply_payload',lambda *a:pytest.fail('CRM in receiver'))
    assert post(c).status_code==200
    with Session() as db:
        row=db.scalar(select(MetaWebhookInbox));assert row.status=='pending'
        assert 'Prosz' not in row.payload_ciphertext
        assert unseal('inbox',row.payload_ciphertext)['object']=='instagram'
        assert db.scalar(select(func.count()).select_from(MetaMessage))==0
    def failed(*args):raise RuntimeError('commit unavailable')
    monkeypatch.setattr('backend.meta_inbox.persist',failed)
    assert post(c,event('other')).status_code==503


def test_raw_signature_size_and_event_limits():
    c=client();raw=json.dumps(event(),indent=2).encode()
    assert post(c,raw=raw,signature='sha256=wrong').status_code==403
    assert post(c,raw=raw).status_code==200
    assert post(c,raw=b'x'*65537).status_code==413
    data=event();data['entry'][0]['messaging']*=51
    assert post(c,data).status_code==413
    with Session() as db:assert db.scalar(select(func.count()).select_from(MetaWebhookInbox))==1


def test_parallel_same_mid_webhooks_are_durable_once():
    clients=[client(),client()];data=event('parallel-mid')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda c:post(c,data).status_code,clients))
    assert results==[200,200]
    with Session() as db:assert db.scalar(select(func.count()).select_from(MetaWebhookInbox))==1
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:drain_once(),range(2)))
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(MetaMessage))==1
        assert db.scalar(select(MetaWebhookInbox)).status=='done'


def test_two_workers_and_stale_lease_fencing():
    persist(event());at=datetime.now(timezone.utc)
    first=claim_batch(at);assert len(first)==1
    assert not claim_batch(at)
    # Simulated process crash: lease expires, replacement claims it.
    second=claim_batch(at+timedelta(seconds=121));assert len(second)==1
    assert not process_claim(*first[0],at=at+timedelta(seconds=122))
    assert process_claim(*second[0],at=at+timedelta(seconds=122))
    with Session() as db:assert db.scalar(select(func.count()).select_from(MetaMessage))==1


def test_atomic_processing_rollback_retries_dead_letter(monkeypatch):
    from backend import meta_inbox
    original=meta_inbox.apply_payload
    def fail_after_crm(db,payload):
        original(db,payload);raise RuntimeError('fixture failure after writes')
    monkeypatch.setattr(meta_inbox,'apply_payload',fail_after_crm)
    persist(event());at=datetime.now(timezone.utc)
    for attempt in range(5):
        claims=claim_batch(at);assert len(claims)==1
        assert not process_claim(*claims[0],at=at)
        with Session() as db:
            assert db.scalar(select(func.count()).select_from(MetaMessage))==0
            row=db.scalar(select(MetaWebhookInbox));assert row.status=='failed' and row.attempts==attempt+1
        assert not claim_batch(at)
        at+=timedelta(seconds=301)
    assert not claim_batch(at)
    with Session() as db:
        row=db.scalar(select(MetaWebhookInbox));assert row.dead_letter==1
        assert diagnostics(db,at)['warning']


def test_owner_diagnostics_and_approved_retention(monkeypatch,caplog):
    c=client();persist(event());drain_once()
    assert c.get('/api/meta/inbox/diagnostics').status_code==200
    assert client('rep1').get('/api/meta/inbox/diagnostics').status_code==403
    at=datetime.now(timezone.utc)
    with Session() as db:
        row=db.scalar(select(MetaWebhookInbox));row.processed_at=(at-timedelta(days=8)).isoformat();db.commit();maintenance(db,at)
        assert not db.get(MetaWebhookInbox,row.id).payload_ciphertext
        row.processed_at=(at-timedelta(days=91)).isoformat();db.commit();maintenance(db,at)
        assert not db.get(MetaWebhookInbox,row.id)
    persist(event('pending-alert'))
    with Session() as db:
        row=db.scalar(select(MetaWebhookInbox));row.created_at=(at-timedelta(seconds=301)).isoformat();db.commit()
        monkeypatch.setattr('backend.meta_inbox._last_alert',0)
        maintenance(db,at)
        assert 'requires owner review' in caplog.text
        assert 'pending-alert' not in caplog.text


@pytest.mark.parametrize('failure',['timeout','network','5xx','oauth_http','invalid_scope'])
def test_refresh_transient_preserves_ciphertext_and_retry_budget(monkeypatch,failure,caplog):
    seed_token();before=token()
    class Broken(FakeMeta):
        def get(self,url,**kw):
            if failure=='timeout':raise httpx.ReadTimeout('fixture-sensitive-url')
            if failure=='network':raise httpx.ConnectError('fixture-sensitive-url')
            if failure=='invalid_scope':self.wrong_scope=True;return super().get(url,**kw)
            return httpx.Response(503 if failure=='5xx' else 400,request=httpx.Request('GET',url),json={'error':{'code':190}})
    monkeypatch.setattr(httpx,'Client',Broken);at=datetime.now(timezone.utc)
    for attempt in range(3):
        with pytest.raises(HTTPException) as raised:check('90001',at)
        assert raised.value.status_code==503
        assert token()==before
        with Session() as db:assert not db.get(MetaCredential,'90001').revoked
        with pytest.raises(HTTPException) as early:check('90001',at)
        assert early.value.status_code==409
        at+=timedelta(seconds=301)
    with Session() as db:assert db.get(MetaRefreshState,'90001').status=='failed'
    assert 'fixture-sensitive-url' not in caplog.text


def test_parallel_refresh_single_flight_without_credential_lock(monkeypatch):
    seed_token();started=threading.Event();finish=threading.Event();calls=[]
    class Slow(FakeMeta):
        def get(self,url,**kw):
            calls.append(True);started.set();assert finish.wait(5)
            return super().get(url,**kw)
    monkeypatch.setattr(httpx,'Client',Slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        future=pool.submit(check,'90001');assert started.wait(3)
        try:
            with pytest.raises(HTTPException) as busy:check('90001')
            assert busy.value.status_code==409
            # Credential row can be locked while the provider request is pending.
            with Session() as db:
                db.execute(text("SET LOCAL lock_timeout='500ms'"))
                assert db.scalar(select(MetaCredential).with_for_update(nowait=True))
                db.rollback()
        finally:finish.set()
        assert future.result()['validated']
    assert len(calls)==1


def test_only_explicit_debug_false_revokes(monkeypatch):
    seed_token()
    class Revoked(FakeMeta):fail=True
    monkeypatch.setattr(httpx,'Client',Revoked)
    with pytest.raises(HTTPException):check('90001')
    with Session() as db:
        row=db.get(MetaCredential,'90001');assert row.revoked and not row.token_ciphertext


def test_read_only_profile_independent_modules(monkeypatch):
    c=client();monkeypatch.setenv('META_ENABLED','false')
    monkeypatch.setenv('META_WEBHOOK_VERIFY_ENABLED','true')
    monkeypatch.setenv('META_INGEST_ENABLED','true')
    monkeypatch.setenv('META_CRM_HISTORY_ENABLED','false')
    assert c.get('/api/meta/webhook',params={'hub.mode':'subscribe','hub.verify_token':'synthetic-verify','hub.challenge':'ok'}).text=='ok'
    assert post(c).status_code==200 and drain_once()==0
    assert c.post('/api/meta/oauth/start').status_code==404
    monkeypatch.setenv('META_CRM_HISTORY_ENABLED','true');assert drain_once()==1
    assert c.get('/api/meta/conversations').status_code==200
    assert c.get('/api/meta/inbox/diagnostics').status_code==404


def test_refresh_crash_lease_recovered_with_bounded_budget(monkeypatch):
    seed_token();before=token();at=datetime.now(timezone.utc)
    with Session() as db:
        db.add(MetaRefreshState(account_id='90001',status='checking',attempts=1,lease_token='interrupted',lease_until=(at-timedelta(seconds=1)).isoformat(),next_attempt_at='',last_error=''));db.commit()
    monkeypatch.setattr(httpx,'Client',FakeMeta)
    assert check('90001',at)['validated']
    assert token()==before


def test_stale_invalid_result_cannot_revoke_new_oauth_ciphertext(monkeypatch):
    seed_token();started=threading.Event();finish=threading.Event()
    class SlowRevoked(FakeMeta):
        fail=True
        def get(self,url,**kw):
            started.set();assert finish.wait(5)
            return super().get(url,**kw)
    monkeypatch.setattr(httpx,'Client',SlowRevoked)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(check,'90001');assert started.wait(3)
        try:
            with Session() as db:
                row=db.get(MetaCredential,'90001');row.token_ciphertext=seal('token','new-synthetic-token');db.commit();replacement=row.token_ciphertext
        finally:finish.set()
        with pytest.raises(HTTPException) as stale:future.result()
        assert stale.value.status_code==409
    assert token()==replacement
    with Session() as db:assert not db.get(MetaCredential,'90001').revoked


def test_failed_inbox_payload_preserved_for_owner_review():
    persist(event());at=datetime.now(timezone.utc)
    with Session() as db:
        row=db.scalar(select(MetaWebhookInbox));row.status='failed';row.dead_letter=1;row.created_at=(at-timedelta(days=91)).isoformat();db.commit();maintenance(db,at)
        assert row.payload_ciphertext and db.get(MetaWebhookInbox,row.id)
        assert diagnostics(db,at)['dead_letter']==1


def test_signature_cannot_be_reused_for_reserialized_body():
    c=client();raw=json.dumps(event(),indent=2).encode()
    signature='sha256='+hmac.new(b'synthetic-secret',raw,hashlib.sha256).hexdigest()
    assert post(c,raw=json.dumps(json.loads(raw),separators=(',',':')).encode(),signature=signature).status_code==403
    with Session() as db:assert db.scalar(select(func.count()).select_from(MetaWebhookInbox))==0


def test_independent_flag_legacy_guard_and_oauth_only_config(monkeypatch):
    c=client();monkeypatch.delenv('META_VERIFY_TOKEN')
    # Unmigrated legacy mode still requires the original complete configuration.
    assert c.post('/api/meta/oauth/start').status_code==503
    monkeypatch.setenv('META_OAUTH_ENABLED','true')
    c.base_url='https://testserver'
    assert c.post('/api/meta/oauth/start').status_code==200
    assert c.get('/api/meta/webhook').status_code==503


def test_owner_sees_safe_refresh_state_and_others_do_not(monkeypatch):
    c=client();seed_token()
    with Session() as db:
        db.add(MetaRefreshState(account_id='90001',status='retry',attempts=1,next_attempt_at=now(),lease_until='',lease_token='',last_error='validation_failed'));db.commit()
    response=c.get('/api/meta/status')
    assert response.status_code==200 and response.json()['credential_check']['status']=='retry'
    assert 'synthetic-token' not in response.text and 'token_ciphertext' not in response.text
    assert 'credential_check' not in client('rep1').get('/api/meta/status').json()
