"""Native planning on a fresh synthetic PostgreSQL, never production or Google."""
import os,uuid,subprocess,sys,json
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest,psycopg
from sqlalchemy import create_engine,select,text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from backend.main import app
from backend.db import Base,User,Salon,Activity,now
from backend.security import database,ph
from backend.native_models import NativeBase,Task,Notification
from backend import native_planning as native
from tests.test_api import client,add

@pytest.fixture(scope='module')
def isolated():
    source=make_url(os.environ['DATABASE_URL'])
    if source.database!='focus3_test' or source.host not in ('localhost','127.0.0.1','postgres'):pytest.skip('Needs isolated PostgreSQL')
    name='focus3_native_'+uuid.uuid4().hex[:8];admin=source.set(database='postgres').render_as_string(hide_password=False);target=source.set(database=name).render_as_string(hide_password=False)
    with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
    env={**os.environ,'DATABASE_URL':target,'APP_ENV':'test'}
    engine=create_engine(target.replace('postgresql://','postgresql+psycopg://'),hide_parameters=True)
    yield sessionmaker(engine,expire_on_commit=False),engine,env
    engine.dispose()
    with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name+' WITH (FORCE)')
@pytest.fixture(autouse=True)
def setup(isolated,monkeypatch):
    factory,engine,env=isolated
    NativeBase.metadata.drop_all(engine);Base.metadata.drop_all(engine);Base.metadata.create_all(engine);NativeBase.metadata.create_all(engine)
    with factory() as db:
        for id,role in [('manager','manager'),('rep1','sales'),('rep2','sales')]:db.add(User(id=id,email=id+'@focus.test',name=id,password_hash=ph.hash('TestPassword123!'),role=role))
        db.commit()
    def dependency():
        with factory() as db:yield db
    app.dependency_overrides[database]=dependency;monkeypatch.setattr(native,'Session',factory);monkeypatch.setenv('FOCUS_CALENDAR_SCHEMA_ENABLED','true');monkeypatch.setenv('FOCUS_CALENDAR_ENABLED','true');monkeypatch.setenv('VISIT_PLANNER_ENABLED','true')
    yield factory
    app.dependency_overrides.pop(database,None)
def old_contact(factory,salon,days,kind='call'):
    with factory() as db:
        db.get(Salon,salon['id']).created_at=(datetime.now(timezone.utc)-timedelta(days=100)).isoformat()
        db.add(Activity(id=str(uuid.uuid4()),salon_id=salon['id'],user_id='rep1',kind=kind,body='Syntetyczny wynik',created_at=datetime.combine(native.today()-timedelta(days=days),__import__('datetime').time(12),native.ZONE).astimezone(timezone.utc).isoformat()));db.commit()
def task(c,salon,**kw):return c.post('/api/focus-calendar/tasks',json={'salon_id':salon['id'],'title':'Test','due_at':'2020-01-01T10:00:00Z',**kw})
@pytest.mark.parametrize('days,threshold',[(7,7),(14,14),(30,30),(60,60)])
def test_contact_buckets(setup,days,threshold):
    c=client('rep1');s=add(c);old_contact(setup,s,days)
    row=c.get('/api/focus-calendar/contacts').json()[0]
    assert row['threshold']==threshold and row['days_since_contact']==days
@pytest.mark.parametrize('kind',['created','appointment','agent_draft','follow_up','focus_task'])
def test_non_contact_activity_never_resets_age(setup,kind):
    c=client('rep1');s=add(c);old_contact(setup,s,60);old_contact(setup,s,0,kind)
    assert c.get('/api/focus-calendar/contacts').json()[0]['days_since_contact']==60

def test_never_contacted_and_rbac(setup):
    c=client('rep1');s=add(c)
    row=c.get('/api/focus-calendar/contacts').json()[0];assert row['last_contact_at'] is None and row['days_since_contact'] is None
    assert client('rep2').get('/api/focus-calendar/contacts').json()==[]
    assert client('rep2').put('/api/focus-calendar/contacts/'+s['id']+'/policy',json={'interval_days':4}).status_code==404
    assert client('rep2').get('/api/focus-calendar/contacts?representative_id=rep1').status_code==403

def test_custom_policy_and_priority_order(setup):
    c=client('rep1');b=add(c,'Salon B',priority='B');a=add(c,'Salon A',priority='A+');old_contact(setup,a,14);old_contact(setup,b,60)
    c.put('/api/focus-calendar/contacts/'+a['id']+'/policy',json={'interval_days':30})
    rows=c.get('/api/focus-calendar/contacts').json();assert rows[0]['priority']=='A+' and not rows[0]['requires_contact']
    assert c.put('/api/focus-calendar/contacts/'+a['id']+'/policy',json={'interval_days':0}).status_code==422

def test_parallel_prepare_no_duplicate_and_no_contact(setup):
    c=client('rep1');s=add(c)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:c.post('/api/focus-calendar/prepare').status_code,range(2)))
    assert results==[200,200] and len(c.get('/api/focus-calendar/tasks').json())==1
    assert c.get('/api/focus-calendar/contacts').json()[0]['last_contact_at'] is None

def test_complete_requires_result_and_explicit_real_contact(setup):
    c=client('rep1');s=add(c);r=task(c,s).json()
    assert c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'completed'}).status_code==422
    done=c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'completed','result':'Odbyta rozmowa testowa','contact_kind':'call'})
    assert done.status_code==200 and c.get('/api/focus-calendar/contacts').json()[0]['days_since_contact']==0
    assert c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'completed','result':'powtórka'}).status_code==409

def test_done_without_contact_does_not_change_contact_clock(setup):
    c=client('rep1');s=add(c);r=task(c,s).json()
    assert c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'completed','result':'Nie odebrał'}).status_code==200
    assert c.get('/api/focus-calendar/contacts').json()[0]['last_contact_at'] is None

def test_optout_and_assignment_protect_tasks(setup):
    c=client('rep1');s=add(c);r=task(c,s).json()
    with setup() as db:db.get(Salon,s['id']).owner_id='rep2';db.commit()
    assert c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'in_progress'}).status_code==404
    other=client('rep2')
    with setup() as db:db.get(Salon,s['id']).status='do_not_contact';db.commit()
    assert other.get('/api/focus-calendar/contacts').json()==[]
    assert task(other,s).status_code==409

def test_reminder_dedupe_restart_and_completion(setup):
    c=client('rep1');s=add(c);old_contact(setup,s,0);r=task(c,s).json();native.tick();native.tick()
    assert len(c.get('/api/focus-calendar/notifications').json())==1
    note=c.get('/api/focus-calendar/notifications').json()[0]
    assert client('rep2').post('/api/focus-calendar/notifications/'+note['key']+'/read').status_code==404
    c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'completed','result':'Wykonano bez kontaktu'})
    assert c.get('/api/focus-calendar/notifications').json()==[]

def test_recurring_task_preserves_local_wall_time_across_dst(setup):
    c=client('rep1');s=add(c);r=task(c,s,due_at='2027-03-27T09:00:00+01:00',repeat_days=1).json()
    c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'completed','result':'Test'})
    rows=c.get('/api/focus-calendar/tasks').json();next_task=next(t for t in rows if t['id']!=r['id'])
    assert next_task['due_at']=='2027-03-28T07:00:00+00:00'

def test_manager_report_and_settings_acl(setup):
    c=client('rep1');add(c);m=client();data=m.get('/api/focus-calendar/report').json()
    assert next(r for r in data['team'] if r['representative_id']=='rep1')['neglected']==1
    body={'intervals':{'A+':2,'A':3,'B':4,'C':5},'reminders':[120]}
    assert c.put('/api/focus-calendar/settings/rep2',json=body).status_code==403
    assert m.put('/api/focus-calendar/settings/rep1',json=body).status_code==200

def test_flag_off_denies_writes_and_queries(setup,monkeypatch):
    c=client();monkeypatch.setenv('FOCUS_CALENDAR_ENABLED','invalid')
    assert c.get('/api/focus-calendar/status').json()['enabled'] is False
    assert c.get('/api/focus-calendar/contacts').status_code==404
    assert c.post('/api/focus-calendar/prepare').status_code==404
    assert native.tick() is False

def test_native_migration_preserves_crm_and_marker_rollback(isolated,setup):
    factory,engine,env=isolated;c=client('rep1');add(c)
    from scripts.backup import fingerprint
    before=fingerprint(env['DATABASE_URL'])
    for args in [('stamp','004'),('upgrade','006'),('upgrade','006'),('downgrade','004')]:
        result=subprocess.run([sys.executable,'-m','alembic','-c','native-alembic.ini',*args],env=env,capture_output=True)
        assert result.returncode==0,'Native migration failed'
    assert fingerprint(env['DATABASE_URL'])==before

def test_new_contact_cancels_previous_followup_and_next_cycle_uses_new_evidence(setup):
    c=client('rep1');s=add(c);c.post('/api/focus-calendar/prepare')
    assert c.post('/api/salons/'+s['id']+'/activities',json={'kind':'call','body':'Rzeczywista rozmowa testowa'}).status_code==201
    c.post('/api/focus-calendar/prepare')
    assert all(t['status']=='cancelled' for t in c.get('/api/focus-calendar/tasks').json())

def test_task_reminder_is_reassigned_without_exposing_previous_owner(setup):
    c=client('rep1');s=add(c);old_contact(setup,s,0);task(c,s);native.tick()
    with setup() as db:db.get(Salon,s['id']).owner_id='rep2';db.commit()
    native.tick()
    assert c.get('/api/focus-calendar/notifications').json()==[]
    assert len(client('rep2').get('/api/focus-calendar/notifications').json())==1

def test_month_calendar_uses_warsaw_boundaries(setup):
    c=client('rep1');add(c)
    assert c.get('/api/appointments?day=2027-03-01&days=31').status_code==200
    assert c.get('/api/appointments?day=2027-03-01&days=32').status_code==422

def test_manual_task_duplicate_and_stale_revision(setup):
    c=client('rep1');s=add(c);r=task(c,s).json()
    assert task(c,s).status_code==409
    assert c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'in_progress'}).status_code==200
    assert c.patch('/api/focus-calendar/tasks/'+r['id'],json={'version':1,'status':'cancelled'}).status_code==409

@pytest.mark.parametrize('value,fold,expected',[
 ('2027-03-28T02:30',None,None),
 ('2027-10-31T02:30',None,None),
 ('2027-10-31T02:30',0,'2027-10-31T00:30:00+00:00'),
 ('2027-10-31T02:30',1,'2027-10-31T01:30:00+00:00'),
 ('2027-03-28T09:00',None,'2027-03-28T07:00:00+00:00')])
def test_local_warsaw_time_gap_and_ambiguity(setup,value,fold,expected):
    c=client('rep1');s=add(c)
    response=c.post('/api/focus-calendar/tasks',json={'salon_id':s['id'],'title':'Lokalny termin','local_due':value,'fold':fold})
    if expected is None:assert response.status_code==422
    else:assert response.status_code==201 and response.json()['due_at']==expected

def test_schema_and_feature_switches_are_independent(setup,monkeypatch):
    c=client();monkeypatch.setenv('FOCUS_CALENDAR_ENABLED','false')
    assert native.schema_enabled() and not native.enabled()
    assert c.get('/api/focus-calendar/status').json()['schema_enabled']
    assert c.get('/api/focus-calendar/tasks').status_code==404
    monkeypatch.setenv('FOCUS_CALENDAR_ENABLED','true');monkeypatch.setenv('FOCUS_CALENDAR_SCHEMA_ENABLED','false')
    assert not native.enabled()

def test_saved_settings_are_read_back(setup):
    c=client('rep1');body={'intervals':{'A+':3,'A':5,'B':12,'C':70},'reminders':[120,30]}
    assert c.put('/api/focus-calendar/settings/rep1',json=body).status_code==200
    assert c.get('/api/focus-calendar/settings').json()==body

def test_appointment_has_one_current_reminder_and_none_after_start(setup):
    from backend.db import Appointment
    c=client('rep1');s=add(c);old_contact(setup,s,0)
    with setup() as db:
        start=datetime.now(timezone.utc)+timedelta(minutes=20)
        a=Appointment(id=str(uuid.uuid4()),salon_id=s['id'],user_id='rep1',starts_at=start.isoformat(),ends_at=(start+timedelta(minutes=20)).isoformat(),status='confirmed');db.add(a);db.commit();id=a.id
    native.tick();native.tick()
    assert len(c.get('/api/focus-calendar/notifications').json())==1
    with setup() as db:db.get(Appointment,id).starts_at=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat();db.commit()
    assert c.get('/api/focus-calendar/notifications').json()==[]

def test_task_creation_waits_for_optout_update_and_rechecks(setup):
    import threading
    c=client('rep1');s=add(c);started=threading.Event();done=threading.Event()
    with setup() as db:
        row=db.get(Salon,s['id'],with_for_update=True);row.status='do_not_contact';db.flush()
        def request():
            started.set()
            try:return task(c,s)
            finally:done.set()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(request)
            try:assert started.wait(3) and not done.wait(.2)
            finally:db.commit()
            assert future.result(timeout=10).status_code==409
