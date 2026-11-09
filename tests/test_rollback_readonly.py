"""New emergency startup profile; synthetic local PostgreSQL, never production."""
import asyncio
import json
import socket
import pytest
from scripts import rollback_readonly as rollback
from tests.test_release_native_rehearsal import scenario
from tests.test_release_rehearsal import ROOT,start,stop,wait_for


@pytest.mark.parametrize('value',[None,'','false','TRUE'])
def test_profile_disabled_without_explicit_approval(value):
    env={'APP_ENV':'test','DATABASE_URL':'postgresql://localhost/focus3_test'}
    if value is not None:env['FOCUS_READONLY_ROLLBACK_APPROVED']=value
    with pytest.raises(rollback.Blocked,match='ROLLBACK_APPROVAL_REQUIRED'):rollback.profile(env)


@pytest.mark.parametrize('url',['sqlite:///:memory:','invalid','mysql://localhost/test'])
def test_profile_rejects_non_postgresql_without_exposing_input(url):
    with pytest.raises(rollback.Blocked,match='^ROLLBACK_DATABASE_INVALID$'):
        rollback.profile({'FOCUS_READONLY_ROLLBACK_APPROVED':'true','DATABASE_URL':url})


def test_profile_preserves_tls_and_overrides_writable_options():
    from sqlalchemy.engine import make_url
    env={'FOCUS_READONLY_ROLLBACK_APPROVED':'true','DATABASE_URL':'postgresql://localhost/focus3_test?sslmode=require&options=-c%20default_transaction_read_only%3Doff'}
    env.update({name:'true' for name in rollback.OFF})
    configured=rollback.profile(env)
    url=make_url(configured['DATABASE_URL'])
    assert url.query['sslmode']=='require' and url.query['options']==rollback.OPTIONS
    assert all(configured[name]=='false' for name in rollback.OFF)
    assert configured['WORKER_PAUSED']=='true' and env['META_ENABLED']=='true'


def test_allowlist_blocks_writes_integrations_and_root_has_no_private_cache():
    calls=[]
    async def app(scope,receive,send):
        calls.append(scope['path'])
        await send({'type':'http.response.start','status':200,'headers':[(b'cache-control',b'public')]})
        await send({'type':'http.response.body','body':b'{}'})
    wrapper=rollback.ReadOnlyAPI(app)
    async def request(method,path):
        messages=[]
        async def send(message):messages.append(message)
        async def receive():return {'type':'http.request','body':b''}
        await wrapper({'type':'http','method':method,'path':path},receive,send)
        return messages
    for method,path in [('POST','/api/auth/login'),('DELETE','/api/salons/fixture'),
                        ('GET','/api/meta/oauth/callback'),('GET','/api/google/oauth/callback'),
                        ('GET','/api/export.xlsx'),('GET','/api/discovery/places'),('GET','/docs')]:
        response=asyncio.run(request(method,path));assert response[0]['status']==503
    assert not calls
    async def websocket():
        messages=[]
        async def send(message):messages.append(message)
        await wrapper({'type':'websocket','path':'/api/salons'},None,send)
        return messages
    assert asyncio.run(websocket())==[{'type':'websocket.close','code':1008}]
    assert not calls
    response=asyncio.run(request('GET','/api/salons'))
    assert calls==['/api/salons'] and dict(response[0]['headers'])[b'cache-control']==b'no-store'
    response=asyncio.run(request('GET','/'))
    assert json.loads(response[1]['body'])['writes'] is False


def test_factory_rejects_preinitialized_writable_engine():
    assert 'backend.db' in __import__('sys').modules
    with pytest.raises(rollback.Blocked,match='ROLLBACK_REQUIRES_FRESH_PROCESS'):
        rollback.create_app()


@pytest.mark.parametrize('revision',['007','004','006'])
def test_real_api_profile_on_native_schema_preserves_all_21_tables(scenario,revision):
    import httpx
    from sqlalchemy import text
    from backend.db import User,Salon,LoginSession
    from backend.meta_models import MetaWebhookInbox
    from backend.security import digest,expires
    from scripts.backup import fingerprint
    factory,env,root=scenario
    with factory() as db:
        db.add_all([User(id='synthetic-rep',name='Synthetic rep',email='rep@focus.invalid',role='sales',password_hash='not-a-login'),
                    User(id='synthetic-disabled',name='Synthetic disabled',email='disabled@focus.invalid',role='manager',active=0,password_hash='not-a-login')]);db.flush()
        db.get(Salon,'synthetic-salon-0').owner_id='synthetic-rep'
        for token,user in [('fixture-owner','synthetic-owner'),('fixture-rep','synthetic-rep'),('fixture-disabled','synthetic-disabled')]:
            db.add(LoginSession(token_hash=digest(token),user_id=user,csrf='synthetic-csrf',expires=expires()))
        db.add(MetaWebhookInbox(id='synthetic-retention',dedup_key='synthetic-retention',account_id='synthetic-account',payload_ciphertext='synthetic-never-decrypt',status='done',processed_at='2000-01-01T00:00:00+00:00'))
        db.execute(text('UPDATE alembic_version SET version_num=:version'),{'version':revision});db.commit()
    before=fingerprint(env['DATABASE_URL'],include_metadata=True)
    assert len(before)==21
    with socket.socket() as candidate:candidate.bind(('127.0.0.1',0));port=candidate.getsockname()[1]
    child_env={**env,'PORT':str(port),'FOCUS_READONLY_ROLLBACK_APPROVED':'true'}
    code='''
import os,sys
from scripts.rollback_readonly import create_app,OFF
try:app=create_app()
except Exception:
 print('BLOCKED: readonly rollback startup refused',file=sys.stderr);sys.exit(1)
assert all(os.environ[name]=='false' for name in OFF)
assert 'backend.worker' not in sys.modules and 'scripts.bootstrap' not in sys.modules
from backend.db import engine
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
try:
 with engine.begin() as db:db.execute(text('UPDATE public.users SET active=active'))
except DBAPIError as error:assert error.orig.sqlstate=='25006'
else:raise AssertionError('Database allowed a write')
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=int(os.environ['PORT']),access_log=False,log_level='warning')
'''
    child=start(code,ROOT,child_env)
    try:
        if revision!='007':
            assert child.wait(timeout=15)!=0
        else:
            base=f'http://127.0.0.1:{port}'
            def healthy():
                try:return httpx.get(base+'/api/health',timeout=.5).status_code==200
                except httpx.HTTPError:return False
            wait_for(healthy)
            with httpx.Client(base_url=base,timeout=3) as client:
                assert client.get('/api/salons').status_code==401
                assert client.get('/api/salons',headers={'Cookie':'focus_session=fixture-disabled'}).status_code==401
                owner={'Cookie':'focus_session=fixture-owner'};rep={'Cookie':'focus_session=fixture-rep'}
                response=client.get('/api/salons',headers=owner)
                assert response.json()['total']==3 and response.headers['x-focus-mode']=='rollback-readonly'
                assert client.get('/api/salons',headers=rep).json()['total']==1
                assert client.get('/api/salons/synthetic-salon-1',headers=rep).status_code==404
                assert client.get('/api/salons/synthetic-salon-0/activities',headers=rep).status_code==200
                assert client.get('/api/auth/me',headers=owner).status_code==200
                assert client.get('/api/appointments',headers=owner).status_code==200
                assert client.post('/api/auth/login',json={'email':'synthetic@focus.invalid','password':'not-a-real-password'}).status_code==503
                assert client.post('/api/auth/logout',headers=owner).status_code==503
                assert client.patch('/api/appointments/visit-0',headers=owner,json={'status':'cancelled'}).status_code==503
                assert client.get('/api/meta/oauth/callback',params={'code':'synthetic'},headers=owner).status_code==503
                assert client.get('/api/discovery/places',headers=owner).status_code==503
    finally:stop(child)
    assert fingerprint(env['DATABASE_URL'],include_metadata=True)==before


def test_rescue_recipe_does_not_package_migration_or_worker_startup():
    recipe=(ROOT/'Dockerfile.rollback').read_text()
    assert 'scripts/start.sh' not in recipe and 'COPY migrations' not in recipe
    assert 'scripts.rollback_readonly' in recipe and 'COPY scripts ./' not in recipe
    assert (ROOT/'Dockerfile').read_text().endswith('CMD ["sh","scripts/start.sh"]\n')
