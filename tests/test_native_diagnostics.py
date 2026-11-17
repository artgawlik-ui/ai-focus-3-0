"""Metadata-only diagnostics on an isolated synthetic PostgreSQL database."""
import json
from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event,select
from backend.main import app
from backend.db import Job,Salon
from backend.native_models import NativeBase
from backend.native_notifications import generate
from backend.native_diagnostics import worker_snapshot
from backend import worker_control
from tests.test_native_planning import isolated,setup
from tests.test_api import client
from tests.native_scale_data import seed

@pytest.mark.parametrize('value',[None,'','ON','1','garbage','false'])
def test_diagnostics_flag_is_fail_closed(setup,monkeypatch,value):
    if value is None:monkeypatch.delenv('FOCUS_DIAGNOSTICS_ENABLED',raising=False)
    else:monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED',value)
    assert client().get('/api/focus-calendar/diagnostics').status_code==404

def test_manager_only_and_no_private_payloads(setup,monkeypatch):
    monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED','true')
    assert TestClient(app).get('/api/focus-calendar/diagnostics').status_code==401
    assert client('rep1').get('/api/focus-calendar/diagnostics').status_code==403
    c=client()
    with setup() as db:
        seed(db,1,owners=('rep1',))
        db.add(Job(id='private-job',salon_id='synthetic-salon-000000',user_id='rep1',evidence='PRIVATE_SENTINEL',result='PRIVATE_SENTINEL'));db.commit()
    r=c.get('/api/focus-calendar/diagnostics')
    assert r.status_code==200 and r.json()['agent_jobs']['queued']==1
    assert all(x not in r.text for x in ('PRIVATE_SENTINEL','private-job','rep1','synthetic-salon'))
    assert r.headers['cache-control']=='no-store'

@pytest.mark.parametrize('state,age,signal',[('idle',2,'fresh'),('paused',40,'stale'),('degraded',1,'fresh'),('idle',-60,'unknown'),('PRIVATE_SENTINEL',0,'unknown')])
def test_worker_signal_is_not_cycle_success(tmp_path,monkeypatch,state,age,signal):
    path=tmp_path/'worker.json';monkeypatch.setattr(worker_control,'STATUS_FILE',path)
    instant=datetime.now(timezone.utc)
    path.write_text(json.dumps({'state':state,'at':(instant-timedelta(seconds=age)).isoformat(),'pid':1234,'secret':'PRIVATE_SENTINEL'}))
    result=worker_snapshot(instant)
    assert result['signal']==signal and result['native_last_success_at'] is None
    assert 'pid' not in result and 'PRIVATE_SENTINEL' not in json.dumps(result)

@pytest.mark.parametrize('payload',[None,'bad-json','[]','x'*4097,'{"state":"idle","at":"2026-01-01"}'])
def test_bad_or_missing_status_is_unknown(tmp_path,monkeypatch,payload):
    path=tmp_path/'worker.json';monkeypatch.setattr(worker_control,'STATUS_FILE',path)
    if payload is not None:path.write_text(payload)
    assert worker_snapshot(datetime.now(timezone.utc))['signal']=='unknown'

def test_backlog_tracks_worker_sources_and_deduplication(setup,monkeypatch):
    monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED','true');c=client()
    with setup() as db:seed(db,3,owners=('rep1',))
    first=c.get('/api/focus-calendar/diagnostics').json()['native']['pending_reminders']
    assert first['tasks']==3 and first['visits']==3 and first['oldest_overdue_seconds']>0
    with setup() as db:generate(db);db.commit()
    after=c.get('/api/focus-calendar/diagnostics').json()['native']['pending_reminders']
    assert after['tasks']==after['visits']==0 and after['oldest_due_at'] is None


def test_opt_out_and_inactive_owners_do_not_count(setup,monkeypatch):
    monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED','true');c=client()
    from backend.db import User
    from backend.meta_models import MetaConversation
    with setup() as db:
        seed(db,3,owners=('rep1','rep2'))
        salons=list(db.scalars(select(Salon).order_by(Salon.id)))
        salons[0].status='do_not_contact'
        db.add(MetaConversation(id='synthetic-optout',account_id='test',peer_id='test',salon_id=salons[2].id,opted_out=1))
        db.get(User,'rep2').active=0;db.commit()
    counts=c.get('/api/focus-calendar/diagnostics').json()['native']['pending_reminders']
    assert counts['tasks']==counts['visits']==0


def test_schema_off_does_not_query_optional_tables(setup,isolated,monkeypatch):
    monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED','true');monkeypatch.setenv('FOCUS_CALENDAR_SCHEMA_ENABLED','false')
    c=client();engine=isolated[1];queries=[]
    def capture(conn,cursor,statement,*args):queries.append(statement.lower())
    event.listen(engine,'before_cursor_execute',capture)
    try:result=c.get('/api/focus-calendar/diagnostics').json()
    finally:event.remove(engine,'before_cursor_execute',capture)
    assert not result['native']['available'] and not result['flags']['runtime_enabled']
    assert not any(any(table in q for table in ('focus_tasks','focus_notifications','focus_contact_policies','focus_work_settings')) for q in queries)


def test_runtime_off_does_not_prevent_metadata_or_enable_execution(setup,monkeypatch):
    monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED','true');monkeypatch.setenv('FOCUS_CALENDAR_ENABLED','false')
    result=client().get('/api/focus-calendar/diagnostics').json()
    assert result['native']['available'] and not result['flags']['runtime_enabled']
    assert not result['external_messages'] and not result['retention_execution_available']


def test_missing_optional_schema_is_controlled(setup,isolated,monkeypatch):
    monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED','true');c=client()
    NativeBase.metadata.drop_all(isolated[1])
    response=c.get('/api/focus-calendar/diagnostics')
    assert response.status_code==200 and response.json()['native']['reason']=='schema_or_query_unavailable'
    assert not any(x in response.text for x in ('SELECT','UndefinedTable','postgresql://'))


def test_diagnostics_and_retention_are_read_only(setup,isolated,monkeypatch):
    from scripts.backup import fingerprint
    monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED','true');monkeypatch.setenv('FOCUS_RETENTION_ENABLED','true');c=client()
    with setup() as db:seed(db,3)
    factory,engine,env=isolated;before=fingerprint(env['DATABASE_URL']);writes=[]
    def capture(conn,cursor,statement,*args):
        if statement.lstrip().lower().startswith(('insert','update','delete','alter','drop','create')):writes.append(statement.split()[0])
    event.listen(engine,'before_cursor_execute',capture)
    try:
        assert c.get('/api/focus-calendar/diagnostics').json()['read_only']
        preview=c.get('/api/focus-calendar/retention-preview').json()
        assert preview['dry_run'] and not preview['deletion_implemented']
    finally:event.remove(engine,'before_cursor_execute',capture)
    assert not writes and fingerprint(env['DATABASE_URL'])==before


def test_invalid_queue_timestamp_does_not_break_diagnostics(setup,monkeypatch):
    monkeypatch.setenv('FOCUS_DIAGNOSTICS_ENABLED','true');c=client()
    with setup() as db:
        seed(db,1,owners=('rep1',))
        db.add(Job(id='invalid-time',salon_id='synthetic-salon-000000',user_id='rep1',created_at='PRIVATE_INVALID_TIME'));db.commit()
    response=c.get('/api/focus-calendar/diagnostics')
    assert response.status_code==200 and response.json()['agent_jobs']['queued']==1
    assert response.json()['agent_jobs']['oldest_queued_age_seconds'] is None
    assert 'PRIVATE_INVALID_TIME' not in response.text
