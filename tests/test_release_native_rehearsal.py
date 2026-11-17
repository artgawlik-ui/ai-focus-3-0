"""Real processes and additive schema; synthetic local PostgreSQL only."""
import json,os,subprocess,sys,uuid
from datetime import datetime,timedelta,timezone
from pathlib import Path
import psycopg,pytest
from sqlalchemy import create_engine,select,func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from backend.db import User,Salon,Activity,Appointment,Job
from backend.native_models import Task,Notification
from scripts.backup import fingerprint
from tests.test_release_rehearsal import ROOT,OLD,old_tree,start,stop,wait_for

@pytest.fixture
def scenario(tmp_path):
    source=make_url(os.environ['DATABASE_URL'])
    assert source.host in ('localhost','127.0.0.1') and source.database=='focus3_test'
    name='focus3_native_'+uuid.uuid4().hex[:10]
    admin=source.set(database='postgres').render_as_string(hide_password=False)
    url=source.set(database=name).render_as_string(hide_password=False)
    with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
    env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','SYSTEMROOT')}
    env.update(DATABASE_URL=url,APP_ENV='test',CONTROL=str(tmp_path),PYTHONPATH='',META_ENABLED='false',
               META_OAUTH_ENABLED='false',META_WEBHOOK_VERIFY_ENABLED='false',META_INGEST_ENABLED='false',
               META_CRM_HISTORY_ENABLED='false',META_DIAGNOSTICS_ENABLED='false',META_DM_TRANSPORT_ENABLED='false',
               GOOGLE_SCHEMA_ENABLED='false',GOOGLE_CALENDAR_ENABLED='false',GOOGLE_CALENDAR_WRITE_ENABLED='false',
               FOCUS_CALENDAR_SCHEMA_ENABLED='true',FOCUS_CALENDAR_ENABLED='true',FOCUS_DIAGNOSTICS_ENABLED='false',
               OFFSITE_BACKUP_ENABLED='false',AI_PAID_PROCESSING_APPROVED='false',WORKER_PAUSED='false')
    engine=create_engine(url.replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
    factory=sessionmaker(engine,expire_on_commit=False)
    try:
        result=subprocess.run([sys.executable,'-m','alembic','-c','native-alembic.ini','upgrade','head'],cwd=ROOT,env=env,capture_output=True,timeout=30)
        assert result.returncode==0,'Synthetic native migration failed'
        now=datetime.now(timezone.utc)
        with factory() as db:
            db.add(User(id='synthetic-owner',email='synthetic@focus.invalid',name='Synthetic',role='manager',password_hash='not-a-login-hash'));db.flush()
            for i in range(3):
                sid='synthetic-salon-'+str(i)
                db.add(Salon(id=sid,owner_id='synthetic-owner',name='[SYNTHETIC] Salon '+str(i),city='Syntetyczne',status='do_not_contact' if i==2 else 'prospect',dedup_key=sid));db.flush()
                db.add(Activity(id='contact-'+str(i),salon_id=sid,user_id='synthetic-owner',kind='call',body='Synthetic real-contact fixture',created_at=now.isoformat()))
                db.add(Task(id='task-'+str(i),salon_id=sid,assignee_id='synthetic-owner',title='Synthetic',due_at=(now-timedelta(hours=1)).isoformat()))
                db.add(Appointment(id='visit-'+str(i),salon_id=sid,user_id='synthetic-owner',starts_at=(now+timedelta(hours=1)).isoformat(),ends_at=(now+timedelta(hours=1,minutes=20)).isoformat(),status='confirmed'))
            db.add(Job(id='allowed-job',salon_id='synthetic-salon-0',user_id='synthetic-owner'))
            db.add(Job(id='blocked-job',salon_id='synthetic-salon-2',user_id='synthetic-owner'));db.commit()
        yield factory,env,tmp_path
    finally:
        engine.dispose()
        with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name+' WITH (FORCE)')

WORKER='''
import os,runpy,time,httpx
from pathlib import Path
from backend import worker_control,native_planning
root=Path(os.environ['CONTROL']);label=os.environ['LABEL']
worker_control.PAUSE_FILE=root/(label+'.pause');worker_control.STATUS_FILE=root/(label+'.json')
def forbidden(*a,**k):raise AssertionError('External HTTP forbidden')
httpx.HTTPTransport.handle_request=forbidden;httpx.AsyncHTTPTransport.handle_async_request=forbidden
if label=='previous':
 original=native_planning.reminders
 def gated(db):
  value=original(db);(root/'before-commit').touch()
  while not (root/'release').exists():time.sleep(.02)
  return value
 native_planning.reminders=gated
runpy.run_module('backend.worker',run_name='__main__')
'''

def state(path):
    try:return json.loads(path.read_text())['state']
    except (OSError,ValueError,KeyError):return None

@pytest.mark.parametrize('forced',[False,True])
def test_native_transaction_handoff_restart_and_readonly_legacy_api(scenario,forced):
    factory,env,root=scenario
    for label in ('previous','current'):(root/(label+'.pause')).touch()
    previous=start(WORKER,ROOT,{**env,'LABEL':'previous'});current=None
    try:
        wait_for(lambda:state(root/'previous.json')=='paused')
        with factory() as db:assert db.scalar(select(func.count()).select_from(Notification))==0
        (root/'previous.pause').unlink();wait_for(lambda:(root/'before-commit').exists())
        # Real INSERTs are not visible to a separate connection before the atomic commit.
        with factory() as db:assert db.scalar(select(func.count()).select_from(Notification))==0
        current=start(WORKER,ROOT,{**env,'LABEL':'current'})
        wait_for(lambda:state(root/'current.json')=='paused')
        if forced:previous.kill()
        else:previous.terminate();(root/'release').touch()
        previous.wait(timeout=8);assert previous.poll() is not None
        with factory() as db:
            assert db.scalar(select(func.count()).select_from(Notification))==(0 if forced else 4)
            assert db.get(Job,'allowed-job').status=='queued'
        (root/'current.pause').unlink()
        def done():
            with factory() as db:return db.get(Job,'allowed-job').status=='completed' and db.get(Job,'blocked-job').status=='failed'
        wait_for(done);stop(current)
        assert state(root/'current.json')=='stopped'
        with factory() as db:
            keys=list(db.scalars(select(Notification.key)))
            assert len(keys)==len(set(keys))==4
            assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind=='agent_draft'))==1
            assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind=='call'))==3
            assert db.scalar(select(func.count()).select_from(Task))==3
        before=fingerprint(env['DATABASE_URL'],include_metadata=True)
        assert len(before)==21 and before['focus_notifications']['count']==4
        # Fresh process/cycle after restart: no extra notification, draft or contact.
        restarted=start("import os; from backend.native_planning import tick; assert tick()",ROOT,env)
        try:assert restarted.wait(timeout=15)==0
        finally:stop(restarted)
        assert fingerprint(env['DATABASE_URL'],include_metadata=True)==before
        # Old API only, no old supervisor/bootstrap/migration/worker on schema007.
        old=old_tree(root)
        rollback=start('''
from types import SimpleNamespace
from fastapi.testclient import TestClient
from backend.main import app
from backend.security import current
c=TestClient(app)
assert c.get('/api/health').status_code==200
assert c.get('/api/salons').status_code==401
app.dependency_overrides[current]=lambda:SimpleNamespace(id='synthetic-owner',role='manager')
r=c.get('/api/salons');assert r.status_code==200 and r.json()['total']==3
''',old,env)
        try:assert rollback.wait(timeout=15)==0
        finally:stop(rollback)
        assert fingerprint(env['DATABASE_URL'],include_metadata=True)==before
    finally:
        if current:stop(current)
        stop(previous)


def test_legacy_default_migration_cannot_be_used_as_native_rollback(scenario):
    factory,env,root=scenario;old=old_tree(root)
    files=subprocess.check_output(['git','ls-tree','-r','--name-only',OLD,'migrations','alembic.ini'],cwd=ROOT,text=True).splitlines()
    for name in files:
        dest=old/name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(subprocess.check_output(['git','show',OLD+':'+name],cwd=ROOT))
    before=fingerprint(env['DATABASE_URL'],include_metadata=True)
    result=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=old,env=env,capture_output=True,timeout=15)
    output=result.stdout+result.stderr
    assert result.returncode!=0 and b'007' in output and b'revision' in output
    assert fingerprint(env['DATABASE_URL'],include_metadata=True)==before
