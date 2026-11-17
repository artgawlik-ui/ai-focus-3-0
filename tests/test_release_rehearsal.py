"""Real local processes, synthetic PG only. No Render or provider transport."""
import json,os,signal,subprocess,sys,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest
from sqlalchemy import select
from tests.test_api import clean,client,add
from backend.db import Session,engine,Job,Activity
from backend.meta_models import MetaConversation

ROOT=Path(__file__).resolve().parents[1]
OLD='d15265b26524d594bdbcb4bc6b63fcbc398a1424'


def wait_for(predicate,seconds=15):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.1)
    raise AssertionError('Synthetic process checkpoint timed out')


def stop(p):
    if p.poll() is None:
        p.terminate()
        try:p.wait(timeout=8)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)


def old_tree(tmp):
    root=tmp/'old';root.mkdir()
    files=subprocess.check_output(['git','ls-tree','-r','--name-only',OLD,'backend'],cwd=ROOT,text=True).splitlines()
    for name in files:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(subprocess.check_output(['git','show',OLD+':'+name],cwd=ROOT))
    return root


def environment(tmp):
    from sqlalchemy.engine import make_url
    url=make_url(os.environ['DATABASE_URL'])
    assert engine.dialect.name=='postgresql' and url.host in ('localhost','127.0.0.1') and url.database=='focus3_test'
    # Whitelist environment: do not inherit integration secrets or production auth.
    env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','SYSTEMROOT')}
    env.update(DATABASE_URL=os.environ['DATABASE_URL'],APP_ENV='test',META_ENABLED='false',
               AI_PAID_PROCESSING_APPROVED='false',OFFSITE_BACKUP_ENABLED='false',AGENT_V2_ENABLED='true',
               CONTROL=str(tmp),PYTHONPATH='')
    return env


def start(code,root,env):
    return subprocess.Popen([sys.executable,'-c',code],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


@pytest.mark.parametrize('forced',[False,True])
def test_old_to_paused_new_resume_and_readonly_code_rollback(tmp_path,forced):
    if engine.dialect.name!='postgresql':pytest.skip('Requires isolated PostgreSQL')
    env=environment(tmp_path);old=old_tree(tmp_path)
    # clean creates ORM tables; add the metadata marker for all-17-table comparison.
    # Actual migration execution is covered separately by test_meta_migration/CI.
    subprocess.run([sys.executable,'-m','alembic','stamp','004'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    c=client();salon=add(c)
    assert c.post('/api/agent/jobs',json={'salon_id':salon['id']}).status_code==202
    # Synthetic provider stub blocks old worker in-flight; no real HTTP is possible.
    oldcode='''
import os,time,runpy,httpx
from pathlib import Path
root=Path(os.environ['CONTROL'])
def forbidden(*a,**k):raise AssertionError('Real HTTP forbidden')
httpx.HTTPTransport.handle_request=forbidden
httpx.AsyncHTTPTransport.handle_async_request=forbidden
def questions(*a,**k):
    (root/'entered').touch()
    while not (root/'release').exists():time.sleep(.05)
    return httpx.Response(200,json={'choices':[{'message':{'content':'Synthetic question'}}]},request=httpx.Request('POST','https://test.invalid'))
httpx.post=questions
runpy.run_module('backend.worker',run_name='__main__')
'''
    oldenv={**env,'AI_PAID_PROCESSING_APPROVED':'true','OPENAI_API_KEY':'synthetic-never-used'}
    pause=tmp_path/'pause';pause.touch();status=tmp_path/'status.json'
    newcode='''
import os,runpy,httpx
from pathlib import Path
from backend import worker_control
root=Path(os.environ['CONTROL'])
worker_control.PAUSE_FILE=root/'pause';worker_control.STATUS_FILE=root/'status.json'
def forbidden(*a,**k):raise AssertionError('Real HTTP forbidden')
httpx.HTTPTransport.handle_request=forbidden
httpx.AsyncHTTPTransport.handle_async_request=forbidden
runpy.run_module('backend.worker',run_name='__main__')
'''
    previous=start(oldcode,old,oldenv);current=None
    try:
        wait_for(lambda:(tmp_path/'entered').exists())
        current=start(newcode,ROOT,env)
        def paused():
            return status.exists() and json.loads(status.read_text())['state']=='paused'
        wait_for(paused)
        with Session() as db:
            assert db.scalar(select(Job)).status=='running'
            assert not list(db.scalars(select(Activity).where(Activity.kind=='agent_draft')))
        if forced:previous.kill()
        else:previous.terminate();(tmp_path/'release').touch()
        previous.wait(timeout=8)
        assert previous.poll() is not None  # verify old exit before resuming new
        if forced:
            with Session() as db:
                job=db.scalar(select(Job));assert job.status=='running'
                # Advance synthetic lease age, not a production recovery instruction.
                job.updated_at=(datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat();db.commit()
        pause.unlink()
        def completed():
            with Session() as db:return db.scalar(select(Job)).status=='completed'
        wait_for(completed)
        stop(current)
        assert json.loads(status.read_text())['state']=='stopped'
        with Session() as db:
            assert len(list(db.scalars(select(Activity).where(Activity.kind=='agent_draft'))))==1
        from scripts.backup import fingerprint
        before=fingerprint(os.environ['DATABASE_URL'],include_metadata=True)
        # Actual old API/ORM, no migration or worker, same current synthetic schema.
        rollback=start("from fastapi.testclient import TestClient; from backend.main import app; c=TestClient(app); assert c.get('/api/health').status_code==200; assert c.get('/api/salons').status_code==401",old,env)
        try:assert rollback.wait(timeout=15)==0
        finally:stop(rollback)
        assert fingerprint(os.environ['DATABASE_URL'],include_metadata=True)==before
        assert len(before)==17
    finally:
        if current:stop(current)
        stop(previous)


def test_failed_real_worker_start_reaps_api(tmp_path):
    if engine.dialect.name!='postgresql':pytest.skip('Requires isolated PostgreSQL')
    env=environment(tmp_path);env['PORT']='0'
    code='''
import os,subprocess
from pathlib import Path
from scripts import supervise
original=subprocess.Popen
def spawn(command):
    if command[2]=='backend.worker':command=[command[0],'-c','raise SystemExit(23)']
    p=original(command)
    if command[2]=='uvicorn':Path(os.environ['CONTROL'],'api.pid').write_text(str(p.pid))
    return p
supervise.subprocess.Popen=spawn
raise SystemExit(supervise.main())
'''
    process=start(code,ROOT,env)
    try:
        assert process.wait(timeout=15)==23
        pid=int((tmp_path/'api.pid').read_text())
        with pytest.raises(ProcessLookupError):os.kill(pid,0)
    finally:stop(process)


def test_queue_rejects_persistent_optout_without_job():
    c=client();salon=add(c)
    with Session() as db:
        db.add(MetaConversation(id='synthetic-optout',account_id='synthetic-account',peer_id='synthetic-peer',salon_id=salon['id'],opted_out=1));db.commit()
    assert c.post('/api/agent/jobs',json={'salon_id':salon['id']}).status_code==409
    with Session() as db:assert db.scalar(select(Job)) is None
