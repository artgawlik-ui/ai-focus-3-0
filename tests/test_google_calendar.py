"""All provider I/O mocked; Google schema isolated from legacy focus3_test."""
import base64,hashlib,json,os,subprocess,sys,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import httpx,psycopg,pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine,select,text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from backend.main import app
from backend.db import Base,User,Salon,Appointment,now
from backend.security import database,ph
from backend.google_models import GoogleBase,GoogleAccount,GoogleOAuthState,GoogleSyncRequest,GoogleEventLink
from backend import google_calendar as google,google_transport as transport
from backend.visit_planner import revision
from tests.test_api import client,add

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def isolated():
    source=make_url(os.environ['DATABASE_URL'])
    if source.host not in ('localhost','127.0.0.1','postgres') or source.database!='focus3_test':pytest.skip('Requires isolated PostgreSQL')
    name='focus3_google_'+uuid.uuid4().hex[:10]
    admin=source.set(database='postgres').render_as_string(hide_password=False)
    target=source.set(database=name).render_as_string(hide_password=False)
    with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
    env={**os.environ,'DATABASE_URL':target,'APP_ENV':'test'}
    result=subprocess.run([sys.executable,'-m','alembic','-c','google-alembic.ini','upgrade','005'],cwd=ROOT,env=env,capture_output=True)
    assert result.returncode==0,'Google test migration failed'
    engine=create_engine(target.replace('postgresql://','postgresql+psycopg://'),hide_parameters=True,pool_size=4,max_overflow=0)
    factory=sessionmaker(engine,expire_on_commit=False)
    yield factory,env,engine
    engine.dispose()
    with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name+' WITH (FORCE)')

class Provider:
    def __init__(self):self.events={};self.calls=[];self.oauth=[];self.count=0;self.fail=0;self.timeout_after_insert=False;self.invalid_grant=False;self.expire_access=False;self.token_fail=0;self.fail_patch=False
    def response(self,code,data):return httpx.Response(code,json=data,request=httpx.Request('POST','https://synthetic.invalid'))
    def token(self,url,**kw):
        assert url=='https://oauth2.googleapis.com/token' and kw['follow_redirects'] is False
        self.oauth.append(kw['data'])
        if self.token_fail:return self.response(self.token_fail,{})
        if self.invalid_grant:return self.response(400,{'error':'invalid_grant'})
        return self.response(200,{'access_token':'synthetic-access','refresh_token':'synthetic-refresh','expires_in':3600,'scope':transport.SCOPE})
    def request(self,method,url,**kw):
        assert url.startswith('https://www.googleapis.com/calendar/v3/') and kw['follow_redirects'] is False
        assert 'access_token' not in url and 'synthetic' not in url
        self.calls.append((method,url,kw))
        if self.fail:
            code=self.fail;self.fail=0;return self.response(code,{})
        if self.expire_access:
            self.expire_access=False;return self.response(401,{})
        path=urlsplit(url).path
        if path.endswith('/calendars'):
            return self.response(200,{'id':'dedicated-calendar'})
        if method=='GET':return self.response(200,self.events[path]) if path in self.events else self.response(404,{})
        if method=='POST':
            data=dict(kw['json']);key=path+'/'+data['id']
            if key in self.events:return self.response(409,{})
            self.count+=1;data['etag']='etag-'+str(self.count);self.events[key]=data
            if self.timeout_after_insert:self.timeout_after_insert=False;raise httpx.ReadTimeout('synthetic-secret-provider-detail')
            return self.response(200,data)
        if method=='PATCH':
            if self.fail_patch:self.fail_patch=False;return self.response(412,{})
            if kw['headers'].get('If-Match')!=self.events[path]['etag']:return self.response(412,{})
            self.count+=1;self.events[path]={**self.events[path],**kw['json'],'etag':'etag-'+str(self.count)}
            return self.response(200,self.events[path])
        raise AssertionError('Unexpected provider method')

@pytest.fixture(autouse=True)
def setup(isolated,monkeypatch):
    factory,env,engine=isolated
    GoogleBase.metadata.drop_all(engine);Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine);GoogleBase.metadata.create_all(engine)
    with factory() as db:
        password=ph.hash('TestPassword123!')
        for id,role in [('manager','manager'),('rep1','sales'),('rep2','sales')]:db.add(User(id=id,email=id+'@focus.test',name=id,password_hash=password,role=role))
        db.commit()
    def dependency():
        with factory() as db:yield db
    app.dependency_overrides[database]=dependency
    monkeypatch.setattr(google,'Session',factory)
    for key,value in {'APP_ENV':'test','APP_ORIGIN':'https://testserver','GOOGLE_SCHEMA_ENABLED':'true','GOOGLE_CALENDAR_ENABLED':'true','GOOGLE_CALENDAR_WRITE_ENABLED':'true','GOOGLE_CLIENT_ID':'synthetic-client','GOOGLE_CLIENT_SECRET':'synthetic-client-secret','GOOGLE_REDIRECT_URI':'https://testserver/api/google-calendar/oauth/callback','GOOGLE_ENCRYPTION_KEY':Fernet.generate_key().decode(),'VISIT_PLANNER_ENABLED':'true'}.items():monkeypatch.setenv(key,value)
    provider=Provider();monkeypatch.setattr(httpx,'post',provider.token);monkeypatch.setattr(httpx,'request',provider.request)
    yield factory,provider
    app.dependency_overrides.pop(database,None)


def authorize(c):
    result=c.post('/api/google-calendar/oauth/start');assert result.status_code==200
    params=parse_qs(urlsplit(result.json()['authorization_url']).query)
    assert c.get('/api/google-calendar/oauth/callback',params={'state':params['state'][0],'code':uuid.uuid4().hex},follow_redirects=False).status_code==303
    assert c.get('/api/google-calendar/status').json()['connected']
    return params


def ready():
    rep=client('rep1');authorize(rep);manager=client()
    assert manager.post('/api/google-calendar/accounts/rep1/approve').status_code==200
    assert manager.post('/api/google-calendar/accounts/rep1/calendar').status_code==200
    return rep,manager


def appointment(rep,manager):
    salon=add(rep)
    result=manager.post('/api/appointments',json={'salon_id':salon['id'],'starts_at':'2027-04-01T10:00:00Z','minutes':20,'status':'confirmed','confirmation_recorded':True})
    assert result.status_code==201
    return result.json()


def enqueue(manager,a,id=None):
    rows=manager.get('/api/appointments').json();row=next(x for x in rows if x['id']==a['id'])
    preview=manager.get('/api/google-calendar/sync-preview/'+a['id']).json()
    return manager.post('/api/google-calendar/sync/'+a['id'],json={'request_id':id or str(uuid.uuid4()),'approval_revision':row['revision'],'approval_payload_hash':preview['payload_hash']})


def retry_now(factory):
    with factory() as db:
        job=db.scalar(select(GoogleSyncRequest).where(GoogleSyncRequest.status=='retry'));job.next_attempt_at='';db.commit()


def test_oauth_state_pkce_csrf_session_and_replay(setup):
    factory,provider=setup;rep=client('rep1');other=client('rep2')
    assert rep.post('/api/google-calendar/oauth/start',headers={'X-CSRF-Token':''}).status_code==403
    result=rep.post('/api/google-calendar/oauth/start').json();params=parse_qs(urlsplit(result['authorization_url']).query)
    assert params['scope']==[transport.SCOPE] and params['code_challenge_method']==['S256']
    assert 'code_verifier' not in result['authorization_url']
    assert other.get('/api/google-calendar/oauth/callback',params={'state':params['state'][0],'code':'synthetic-code'}).status_code==403
    args={'state':params['state'][0],'code':'synthetic-code'}
    assert rep.get('/api/google-calendar/oauth/callback',params=args,follow_redirects=False).status_code==303
    verifier=provider.oauth[-1]['code_verifier']
    assert base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')==params['code_challenge'][0]
    assert rep.get('/api/google-calendar/oauth/callback',params=args).status_code==403
    with factory() as db:
        a=db.get(GoogleAccount,'rep1');assert 'synthetic-access' not in a.tokens_ciphertext and 'synthetic-refresh' not in a.tokens_ciphertext
        assert db.scalar(select(GoogleOAuthState)).verifier_ciphertext==''


def test_oauth_expiry_error_and_duplicate_code(setup):
    factory,provider=setup;c=client('rep1')
    params=authorize(c)
    fresh=parse_qs(urlsplit(c.post('/api/google-calendar/oauth/start').json()['authorization_url']).query)
    used=provider.oauth[0]['code']
    assert c.get('/api/google-calendar/oauth/callback',params={'state':fresh['state'][0],'code':used}).status_code==403
    fresh=parse_qs(urlsplit(c.post('/api/google-calendar/oauth/start').json()['authorization_url']).query)
    with factory() as db:
        state=db.get(GoogleOAuthState,hashlib.sha256(fresh['state'][0].encode()).hexdigest());state.expires_at='2000-01-01';db.commit()
    assert c.get('/api/google-calendar/oauth/callback',params={'state':fresh['state'][0],'code':'another'}).status_code==403
    fresh=parse_qs(urlsplit(c.post('/api/google-calendar/oauth/start').json()['authorization_url']).query)
    r=c.get('/api/google-calendar/oauth/callback',params={'state':fresh['state'][0],'error':'access_denied','error_reason':'synthetic-secret'},follow_redirects=False)
    assert r.headers['location']=='/?google_calendar=cancelled' and 'synthetic-secret' not in str(r.headers)


def test_manager_approval_and_idempotent_calendar_creation(setup):
    _,provider=setup;rep=client('rep1');authorize(rep)
    assert rep.post('/api/google-calendar/accounts/rep1/approve').status_code==403
    manager=client()
    assert manager.post('/api/google-calendar/accounts/rep1/calendar').status_code==409
    assert manager.post('/api/google-calendar/accounts/rep1/approve').status_code==200
    assert manager.post('/api/google-calendar/accounts/rep1/calendar').json()['created']
    assert manager.post('/api/google-calendar/accounts/rep1/calendar').json()['created'] is False
    assert len(provider.calls)==1


def test_transport_switch_is_independent_fail_closed(setup,monkeypatch):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager)
    assert enqueue(manager,a).status_code==202
    before=len(provider.calls)
    monkeypatch.delenv('GOOGLE_CALENDAR_WRITE_ENABLED')
    assert google.process_once() is False
    with factory() as db:
        account=db.get(GoogleAccount,'rep1')
        with pytest.raises(transport.ProviderError):transport.calendar_request(account,'POST','calendars',{})
    assert len(provider.calls)==before
    for value in ('','invalid','false'):
        monkeypatch.setenv('GOOGLE_CALENDAR_WRITE_ENABLED',value);assert not transport.writable()


def test_create_map_and_repeat_requests_are_idempotent(setup):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);request=str(uuid.uuid4())
    first=enqueue(manager,a,request).json();assert enqueue(manager,a,request).json()['id']==first['id']
    assert enqueue(manager,a).json()['id']==first['id']
    assert rep.post('/api/google-calendar/sync/'+a['id'],json={'request_id':str(uuid.uuid4()),'approval_revision':'a'*64,'approval_payload_hash':'b'*64}).status_code==403
    assert google.process_once()
    assert len(provider.events)==1
    assert enqueue(manager,a).json()['status']=='already_synced'
    assert client('rep2').get('/api/google-calendar/requests').json()==[]
    with factory() as db:
        assert db.get(GoogleEventLink,a['id']).user_id=='rep1'
        assert db.get(GoogleSyncRequest,first['id']).status=='synced'


def test_update_and_cancel_use_if_match_without_duplicates(setup):
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager)
    enqueue(manager,a);google.process_once()
    assert manager.patch('/api/appointments/'+a['id'],json={'status':'confirmed','confirmation_recorded':True,'starts_at':'2027-04-02T10:00:00Z'}).status_code==200
    enqueue(manager,a);google.process_once()
    assert len(provider.events)==1
    assert manager.patch('/api/appointments/'+a['id'],json={'status':'cancelled'}).status_code==200
    enqueue(manager,a);google.process_once()
    assert next(iter(provider.events.values()))['status']=='cancelled'
    assert all(call[2]['headers'].get('If-Match') for call in provider.calls if call[0]=='PATCH')
    assert not any(call[0]=='DELETE' for call in provider.calls)


def test_stale_appointment_is_never_sent(setup):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a)
    before=len(provider.calls)
    manager.patch('/api/appointments/'+a['id'],json={'status':'confirmed','confirmation_recorded':True,'notes':'Changed'})
    # Notes are deliberately not exported, but local approval must still bind all visit fields.
    assert google.process_once()
    assert len(provider.calls)==before
    assert manager.get('/api/google-calendar/requests').json()[0]['last_error']=='appointment_changed'


@pytest.mark.parametrize('failure',[429,500])
def test_transient_provider_retains_tokens_and_retries(setup,failure):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);provider.fail=failure
    google.process_once();assert manager.get('/api/google-calendar/requests').json()[0]['status']=='retry'
    with factory() as db:assert db.get(GoogleAccount,'rep1').tokens_ciphertext
    retry_now(factory);google.process_once();assert len(provider.events)==1


def test_timeout_after_create_adopts_event_without_second_insert(setup,caplog):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);provider.timeout_after_insert=True
    google.process_once();retry_now(factory);google.process_once()
    assert len(provider.events)==1
    assert len([x for x in provider.calls if x[0]=='POST' and '/events' in x[1]])==1
    assert manager.get('/api/google-calendar/requests').json()[0]['status']=='synced'
    assert 'synthetic-secret-provider-detail' not in caplog.text


def test_remote_etag_conflict_is_not_overwritten(setup):
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);google.process_once()
    next(iter(provider.events.values()))['etag']='externally-changed'
    manager.patch('/api/appointments/'+a['id'],json={'status':'confirmed','confirmation_recorded':True,'minutes':15})
    enqueue(manager,a);google.process_once()
    assert manager.get('/api/google-calendar/requests').json()[0]['last_error']=='remote_conflict'
    assert not any(x[0]=='PATCH' for x in provider.calls)


@pytest.mark.parametrize('invalid',[False,True])
def test_expired_token_refresh_and_invalid_grant(setup,invalid):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a)
    with factory() as db:
        account=db.get(GoogleAccount,'rep1');value=transport.unseal(account.tokens_ciphertext);value['expires_at']='2000-01-01T00:00:00+00:00';account.tokens_ciphertext=transport.seal(value);db.commit()
    provider.invalid_grant=invalid;google.process_once()
    with factory() as db:
        account=db.get(GoogleAccount,'rep1')
        assert bool(account.revoked)==invalid
        assert bool(account.tokens_ciphertext)!=invalid
    if not invalid:assert len(provider.events)==1


def test_disconnect_clears_tokens_and_blocks_pending_requests(setup):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);before=len(provider.calls)
    assert rep.post('/api/google-calendar/disconnect').json()['disconnected']
    assert not google.process_once()
    assert len(provider.calls)==before
    with factory() as db:
        assert not db.get(GoogleAccount,'rep1').tokens_ciphertext
        assert db.scalar(select(GoogleSyncRequest)).status=='cancelled'


def test_parallel_consumers_have_one_external_insert(setup):
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:google.process_once(),range(2)))
    assert results.count(True)==1 and len(provider.events)==1


def test_schema_005_repeat_and_safe_down_migration(isolated,setup):
    factory,env,engine=isolated
    def migrate(*args):return subprocess.run([sys.executable,'-m','alembic','-c','google-alembic.ini',*args],cwd=ROOT,env=env,capture_output=True)
    assert migrate('upgrade','005').returncode==0
    assert migrate('upgrade','005').returncode==0
    assert migrate('check').returncode==0
    with engine.connect() as db:assert db.scalar(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'"))==21
    assert migrate('downgrade','004').returncode==0
    with engine.connect() as db:assert db.scalar(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'"))==21
    assert migrate('upgrade','005').returncode==0
    authorize(client('rep1'))
    from scripts.backup import fingerprint
    before=fingerprint(env['DATABASE_URL'])
    assert migrate('downgrade','004').returncode==0
    assert fingerprint(env['DATABASE_URL'])==before
    with engine.connect() as db:assert db.scalar(text('SELECT version_num FROM alembic_version'))=='004'
    with factory() as db:assert db.get(GoogleAccount,'rep1').tokens_ciphertext


def test_disconnect_invalidates_pending_and_inflight_oauth(setup,monkeypatch):
    import threading
    factory,provider=setup;c=client('rep1')
    params=parse_qs(urlsplit(c.post('/api/google-calendar/oauth/start').json()['authorization_url']).query)
    entered=threading.Event();release=threading.Event();original=provider.token
    def blocked(*a,**kw):entered.set();assert release.wait(10);return original(*a,**kw)
    monkeypatch.setattr(httpx,'post',blocked)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(lambda:c.get('/api/google-calendar/oauth/callback',params={'state':params['state'][0],'code':'synthetic-inflight'},follow_redirects=False))
        try:
            assert entered.wait(5)
            assert c.post('/api/google-calendar/disconnect').status_code==200
        finally:release.set()
        assert future.result(timeout=10).headers['location']=='/?google_calendar=failed'
    assert c.get('/api/google-calendar/status').json()['connected'] is False


def test_uncertain_calendar_creation_is_not_repeated(setup,monkeypatch):
    _,provider=setup;rep=client('rep1');authorize(rep);manager=client();manager.post('/api/google-calendar/accounts/rep1/approve')
    calls=[]
    def lost(*a,**k):calls.append(1);raise httpx.ReadTimeout('synthetic-provider-secret')
    monkeypatch.setattr(httpx,'request',lost)
    assert manager.post('/api/google-calendar/accounts/rep1/calendar').status_code==503
    assert manager.post('/api/google-calendar/accounts/rep1/calendar').status_code==409
    assert len(calls)==1


def test_default_off_status_does_not_touch_google_tables(setup,monkeypatch):
    monkeypatch.delenv('GOOGLE_SCHEMA_ENABLED')
    c=client();status=c.get('/api/google-calendar/status').json()
    assert status['enabled'] is False and status['connected'] is False
    assert c.post('/api/google-calendar/oauth/start').status_code==404


def test_changed_note_alone_invalidates_approval(setup):
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);before=len(provider.calls)
    manager.patch('/api/appointments/'+a['id'],json={'status':'confirmed','confirmation_recorded':True,'notes':'Nowa lokalna notatka'})
    google.process_once()
    assert len(provider.calls)==before
    assert manager.get('/api/google-calendar/requests').json()[0]['last_error']=='appointment_changed'


def test_external_actor_cannot_reuse_request_id_for_other_visit(setup):
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager);request=str(uuid.uuid4());enqueue(manager,a,request)
    with google.Session() as db:
        other=Appointment(id=str(uuid.uuid4()),salon_id=a['salon_id'],user_id='rep1',starts_at='2027-04-03T10:00:00+00:00',ends_at='2027-04-03T10:20:00+00:00',status='confirmed');db.add(other);db.commit();data={'id':other.id}
    assert enqueue(manager,data,request).status_code==409


def test_profile_change_between_preview_and_approval_is_rejected(setup):
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager)
    preview=manager.get('/api/google-calendar/sync-preview/'+a['id']).json()
    with google.Session() as db:
        salon=db.get(Salon,a['salon_id']);salon.name='Nowa syntetyczna nazwa';db.commit()
    response=manager.post('/api/google-calendar/sync/'+a['id'],json={'request_id':str(uuid.uuid4()),'approval_revision':preview['approval_revision'],'approval_payload_hash':preview['payload_hash']})
    assert response.status_code==409


def test_account_approval_does_not_reset_uncertain_creation(setup):
    factory,_=setup;rep,manager=ready()
    with factory() as db:
        a=db.get(GoogleAccount,'rep1');a.calendar_id='';a.status='calendar_creation_uncertain';db.commit()
    assert manager.post('/api/google-calendar/accounts/rep1/approve').status_code==200
    assert manager.post('/api/google-calendar/accounts/rep1/calendar').status_code==409


def test_expired_sync_approval_never_calls_provider(setup):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);before=len(provider.calls)
    with factory() as db:
        job=db.scalar(select(GoogleSyncRequest));job.expires_at='2000-01-01';db.commit()
    google.process_once()
    assert len(provider.calls)==before
    assert manager.get('/api/google-calendar/requests').json()[0]['last_error']=='approval_expired'


def test_401_refreshes_once_without_exposing_tokens(setup,caplog):
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);provider.expire_access=True
    google.process_once()
    assert len(provider.events)==1 and provider.oauth[-1]['grant_type']=='refresh_token'
    public=json.dumps(manager.get('/api/google-calendar/accounts').json())+json.dumps(manager.get('/api/google-calendar/requests').json())+caplog.text
    assert 'synthetic-access' not in public and 'synthetic-refresh' not in public


def test_inactive_salesperson_is_not_synchronized(setup):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);before=len(provider.calls)
    with factory() as db:db.get(User,'rep1').active=0;db.commit()
    google.process_once()
    assert len(provider.calls)==before
    assert manager.get('/api/google-calendar/requests').json()[0]['last_error']=='approval_access_revoked'


def test_retry_limit_is_bounded(setup):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a)
    for attempt in range(5):
        provider.fail=500;google.process_once()
        if attempt<4:retry_now(factory)
    with factory() as db:
        job=db.scalar(select(GoogleSyncRequest));assert job.status=='needs_review' and job.attempts==5


def test_two_parallel_enqueue_requests_share_one_pending_job(setup):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:enqueue(manager,a).json()['id'],range(2)))
    assert results[0]==results[1]
    with factory() as db:assert len(list(db.scalars(select(GoogleSyncRequest))))==1


def test_transport_rejects_delete_and_other_calendar(setup):
    factory,provider=setup;ready();before=len(provider.calls)
    with factory() as db:
        account=db.get(GoogleAccount,'rep1')
        for method,path in [('DELETE',transport.event_path(account.calendar_id,'event')),('GET','calendars/another/events')]:
            with pytest.raises(transport.ProviderError):transport.calendar_request(account,method,path)
    assert len(provider.calls)==before


def test_412_during_update_is_never_forced(setup):
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a);google.process_once()
    manager.patch('/api/appointments/'+a['id'],json={'status':'confirmed','confirmation_recorded':True,'minutes':15})
    enqueue(manager,a);provider.fail_patch=True;google.process_once()
    assert manager.get('/api/google-calendar/requests').json()[0]['last_error']=='remote_conflict'
    assert len([x for x in provider.calls if x[0]=='PATCH'])==1


def test_transient_refresh_error_keeps_encrypted_credentials(setup):
    factory,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a)
    with factory() as db:
        account=db.get(GoogleAccount,'rep1');value=transport.unseal(account.tokens_ciphertext);value['expires_at']='2000-01-01T00:00:00+00:00';before=transport.seal(value);account.tokens_ciphertext=before;db.commit()
    provider.token_fail=500;google.process_once()
    with factory() as db:
        account=db.get(GoogleAccount,'rep1');assert account.tokens_ciphertext==before and not account.revoked
    assert manager.get('/api/google-calendar/requests').json()[0]['status']=='retry'


def test_edit_during_provider_call_waits_and_marks_previous_version(setup,monkeypatch):
    import threading
    _,provider=setup;rep,manager=ready();a=appointment(rep,manager);enqueue(manager,a)
    entered=threading.Event();release=threading.Event();attempting=threading.Event();done=threading.Event();original=provider.request;once=[False]
    def blocked(method,url,**kw):
        if '/events' in url and not once[0]:
            once[0]=True;entered.set();assert release.wait(10)
        return original(method,url,**kw)
    monkeypatch.setattr(httpx,'request',blocked)
    with ThreadPoolExecutor(max_workers=2) as pool:
        sync=pool.submit(google.process_once)
        try:
            assert entered.wait(5)
            def update_visit():
                attempting.set()
                try:return manager.patch('/api/appointments/'+a['id'],json={'status':'confirmed','confirmation_recorded':True,'minutes':15})
                finally:done.set()
            edit=pool.submit(update_visit)
            assert attempting.wait(5) and not done.wait(.2)
        finally:release.set()
        assert sync.result(timeout=10)
        assert edit.result(timeout=10).status_code==200
    job=manager.get('/api/google-calendar/requests').json()[0]
    assert job['status']=='synced' and job['matches_local_version'] is False
