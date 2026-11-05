import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock
import pytest
from sqlalchemy import select
from backend import worker,worker_control


@pytest.mark.parametrize('value,expected',[(None,False),('false',False),('ON',True),('',True),('invalid',True)])
def test_pause_fail_closed(monkeypatch,tmp_path,value,expected):
    monkeypatch.setattr(worker_control,'PAUSE_FILE',tmp_path/'pause')
    if value is None:monkeypatch.delenv('WORKER_PAUSED',raising=False)
    else:monkeypatch.setenv('WORKER_PAUSED',value)
    assert worker_control.paused() is expected
    worker_control.PAUSE_FILE.touch()
    assert worker_control.paused()


@pytest.mark.parametrize('stage',['paused','maintenance','meta','job'])
def test_stop_never_starts_next_stage(monkeypatch,stage):
    handlers={};calls=[]
    def register(sig,handler):
        old=handlers.get(sig,signal.SIG_DFL);handlers[sig]=handler;return old
    monkeypatch.setattr(worker.signal if hasattr(worker,'signal') else signal,'signal',register)
    monkeypatch.setattr(worker_control,'paused',lambda:stage=='paused')
    def publish(state):
        calls.append(state)
        if state=='paused':handlers[signal.SIGTERM]()
    monkeypatch.setattr(worker_control,'publish',publish)
    for name,label in [('maintain_meta_once','maintenance'),('process_meta_once','meta'),('run_once','job')]:
        def action(label=label):
            calls.append(label)
            if label==stage:handlers[signal.SIGTERM]()
        monkeypatch.setattr(worker,name,action)
    worker.main()
    assert calls[-1]=='stopped'
    if stage=='paused':assert not any(s in calls for s in ('maintenance','meta','job'))
    if stage=='maintenance':assert 'meta' not in calls and 'job' not in calls
    if stage=='meta':assert 'job' not in calls


def test_status_has_only_operational_fields(monkeypatch,tmp_path):
    import json,stat
    path=tmp_path/'status.json';monkeypatch.setattr(worker_control,'STATUS_FILE',path)
    worker_control.publish('paused')
    assert set(json.loads(path.read_text()))=={'state','pid','at'}
    assert stat.S_IMODE(path.stat().st_mode)==0o600


@pytest.mark.parametrize('old_raises',[False,True])
def test_reclaimed_job_fences_old_executor(monkeypatch,old_raises):
    from tests.test_api import client,add
    from backend.db import Session,engine,Job,Activity
    from backend import agent_provider
    if engine.dialect.name!='postgresql':pytest.skip('Requires isolated PostgreSQL')
    c=client();salon=add(c)
    assert c.post('/api/agent/jobs',json={'salon_id':salon['id']}).status_code==202
    entered=threading.Event();release=threading.Event();counter=[0]
    def slow_provider(*_):
        counter[0]+=1
        if counter[0]==1:
            entered.set();assert release.wait(10)
            if old_raises:raise ValueError('synthetic interruption')
    monkeypatch.setattr(agent_provider,'add_optional_questions',slow_provider)
    with ThreadPoolExecutor(max_workers=1) as pool:
        old=pool.submit(worker.run_once)
        try:
            assert entered.wait(5)
            with Session() as db:
                job=db.scalar(select(Job));job.updated_at=(datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat();db.commit()
            assert worker.run_once()
        finally:release.set()
        assert old.result(timeout=10)
    with Session() as db:
        assert db.scalar(select(Job)).status=='completed'
        assert len(list(db.scalars(select(Activity).where(Activity.kind=='agent_draft'))))==1

from tests.test_api import clean


def test_status_failure_does_not_abort_worker(monkeypatch,tmp_path,caplog):
    monkeypatch.setattr(worker_control,'STATUS_FILE',tmp_path/'missing'/'status.json')
    worker_control.publish('idle')
    assert 'details suppressed' in caplog.text
