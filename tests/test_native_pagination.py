"""All writes use an isolated synthetic PostgreSQL database."""
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import os,subprocess,sys
import pytest
from sqlalchemy import select,event,func,text
from backend import native_planning as native
from backend.native_models import Task,Notification
from backend.db import Salon,Activity,Appointment
from backend.native_notifications import generate
from tests.test_native_planning import isolated,setup
from tests.test_api import client
from tests.native_scale_data import seed

@pytest.mark.parametrize('resource',['contacts','tasks','visits','notifications'])
def test_pages_validate_bounds_and_access(setup,resource):
    a=client('rep1');b=client('rep2')
    with setup() as db:seed(db,45,owners=('rep1',))
    if resource=='notifications':
        with setup() as db:generate(db);db.commit()
    url='/api/focus-calendar/'+resource+'/page'
    assert a.get(url+'?limit=101').status_code==422
    assert a.get(url+'?offset=-1').status_code==422
    assert a.get(url+'?limit=0').status_code==422
    params='&day='+(datetime.now(timezone.utc)+timedelta(hours=1)).astimezone(native.ZONE).date().isoformat() if resource=='visits' else ''
    first=a.get(url+'?limit=20'+params).json();second=a.get(url+'?limit=20&offset=20'+params).json()
    key={'contacts':'salon_id','notifications':'key'}.get(resource,'id')
    assert len(first['items'])==20 and len(second['items'])==20
    assert not ({r[key] for r in first['items']} & {r[key] for r in second['items']})
    assert b.get(url+'?limit=20'+params).json()['total']==0
    if resource!='notifications':assert b.get(url+'?representative_id=rep1').status_code==403

def test_all_pages_have_no_missing_or_duplicate_ids(setup):
    with setup() as db:seed(db,305,owners=('rep1',))
    c=client('rep1');ids=[]
    for offset in range(0,305,100):
        page=c.get('/api/focus-calendar/contacts/page?limit=100&offset='+str(offset)).json()
        assert page['total']==305;ids.extend(r['salon_id'] for r in page['items'])
    assert len(ids)==len(set(ids))==305

@pytest.mark.parametrize('resource,priority',[('contacts','A+'),('tasks','normal'),('visits','A+')])
def test_literal_search_and_filters(setup,resource,priority):
    with setup() as db:seed(db,50,owners=('rep1',))
    c=client('rep1');base='/api/focus-calendar/'+resource+'/page'
    base+='?day='+(datetime.now(timezone.utc)+timedelta(hours=1)).astimezone(native.ZONE).date().isoformat()+'&' if resource=='visits' else '?' 
    assert c.get(base+'search=Salon%20000000&priority='+__import__('urllib.parse',fromlist=['quote']).quote(priority)).json()['total']==1
    assert c.get(base+'search=%25').json()['total']==0
    assert c.get(base+'priority=invalid').status_code==422
    if resource!='visits':assert c.get(base+'from_date=2030-01-02&to_date=2020-01-01').status_code==422

def test_query_count_does_not_grow_per_customer(setup,isolated):
    factory,engine,_=isolated
    with factory() as db:seed(db,300)
    c=client();queries=[]
    def count(*args):queries.append(1)
    event.listen(engine,'before_cursor_execute',count)
    try:
        response=c.get('/api/focus-calendar/contacts/page?limit=20')
        assert response.status_code==200 and response.json()['total']==300
        assert len(queries)<=5
    finally:event.remove(engine,'before_cursor_execute',count)

def test_summary_counts_cover_more_than_the_legacy_limit(setup):
    with setup() as db:seed(db,1105,owners=('rep1',))
    c=client();data=c.get('/api/focus-calendar/report').json()
    assert data['counts']['overdue_tasks']==1105
    assert len(data['tasks'])==20 and data['pages']['tasks']==1105
    rep=next(r for r in data['team'] if r['representative_id']=='rep1')
    assert rep['overdue_tasks']==1105 and rep['neglected']==1105

def test_batches_do_not_starve_later_reminders(setup):
    with setup() as db:seed(db,1205,owners=('rep1',))
    counts=[]
    for _ in range(4):
        with setup() as db:counts.append(generate(db));db.commit()
    with setup() as db:
        assert db.scalar(select(func.count()).select_from(Notification))==2410
    assert counts==[1000,1000,410,0]

def test_two_workers_do_not_duplicate_current_notifications(setup):
    with setup() as db:seed(db,8,owners=('rep1',))
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:native.tick(),range(2)))
    native.tick()
    with setup() as db:
        notices=list(db.scalars(select(Notification.key)))
        assert len(notices)==len(set(notices))
        assert db.scalar(select(func.count()).select_from(Activity).where(Activity.kind=='call'))==8

def test_stale_feed_cannot_hide_current_notification(setup):
    with setup() as db:
        seed(db,1,owners=('rep1',))
        for i in range(150):db.add(Notification(key='obsolete-'+str(i),user_id='rep1',task_id='synthetic-task-000000',at=datetime.now(timezone.utc).isoformat()))
        db.commit();generate(db);db.commit()
    result=client('rep1').get('/api/focus-calendar/notifications/page').json()
    assert result['total']==2 and len(result['items'])==2

def test_retention_is_read_only_even_when_enabled_is_requested(setup,isolated,monkeypatch):
    factory,engine,env=isolated
    with factory() as db:seed(db,3)
    from scripts.backup import fingerprint
    sales=client('rep1');owner=client();before=fingerprint(env['DATABASE_URL']);monkeypatch.setenv('FOCUS_RETENTION_ENABLED','true')
    assert sales.get('/api/focus-calendar/retention-preview').status_code==403
    result=owner.get('/api/focus-calendar/retention-preview').json()
    assert result['enabled'] is False and result['dry_run'] and not result['deletion_implemented']
    assert fingerprint(env['DATABASE_URL'])==before

def test_optional_indexes_upgrade_repeat_check_and_down(isolated,setup):
    factory,engine,env=isolated
    with factory() as db:seed(db,3)
    from scripts.backup import fingerprint
    before=fingerprint(env['DATABASE_URL'])
    for args in [('stamp','006'),('upgrade','007'),('upgrade','007'),('check',),('downgrade','006')]:
        r=subprocess.run([sys.executable,'-m','alembic','-c','native-alembic.ini',*args],env=env,capture_output=True)
        assert r.returncode==0,'Optional index migration failed'
    with engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM salons"))==3
        assert db.scalar(text("SELECT count(*) FROM pg_indexes WHERE indexname IN ('ix_focus_contact_activity','ix_focus_task_queue','ix_focus_task_salon_cycle','ix_focus_notice_feed','ix_focus_visit_window','ix_focus_meta_optout')"))==0
    assert fingerprint(env['DATABASE_URL'])==before

@pytest.mark.parametrize('resource',['contacts','tasks','visits','notifications'])
def test_legacy_lists_expose_bounds_and_total_headers(setup,resource):
    with setup() as db:seed(db,130,owners=('rep1',));generate(db);db.commit()
    c=client('rep1');url='/api/appointments' if resource=='visits' else '/api/focus-calendar/'+resource
    result=c.get(url)
    assert result.status_code==200 and len(result.json())==100
    assert int(result.headers['X-Focus-Total'])==(260 if resource=='notifications' else 130)
    assert result.headers['X-Focus-Has-More']=='true'
    assert len(c.get(url+'?limit=20&offset=20').json())==20

def test_projection_normalizes_offsets_and_skips_invalid_or_future_evidence(setup):
    with setup() as db:
        seed(db,1,owners=('rep1',))
        at=datetime.now(timezone.utc)-timedelta(days=2)
        for id,value in [('offset',at.astimezone(__import__('datetime').timezone(timedelta(hours=9))).isoformat()),('invalid','invalid-date'),('future',(datetime.now(timezone.utc)+timedelta(days=2)).isoformat())]:
            db.add(Activity(id=id,salon_id='synthetic-salon-000000',user_id='rep1',kind='call',body='Synthetic',created_at=value))
        db.commit()
    row=client('rep1').get('/api/focus-calendar/contacts/page').json()['items'][0]
    assert row['cycle']=='offset' and datetime.fromisoformat(row['last_contact_at'])==at

def test_date_status_priority_filters_respect_warsaw_dst(setup):
    with setup() as db:seed(db,1,owners=('rep1',))
    c=client('rep1')
    for title,due in [('inside','2027-03-27T23:30:00Z'),('outside','2027-03-28T22:30:00Z')]:
        assert c.post('/api/focus-calendar/tasks',json={'salon_id':'synthetic-salon-000000','title':title,'due_at':due,'priority':'high'}).status_code==201
    page=c.get('/api/focus-calendar/tasks/page?from_date=2027-03-28&to_date=2027-03-28&status=planned&priority=high').json()
    assert page['total']==1 and page['items'][0]['title']=='inside'

def test_reschedule_and_cancellation_hide_stale_reminders(setup):
    with setup() as db:seed(db,1,owners=('rep1',));generate(db);db.commit()
    c=client('rep1');m=client();before=c.get('/api/focus-calendar/notifications/page').json()['items']
    old=next(r['key'] for r in before if r['key'].startswith('visit:'))
    changed=(datetime.now(timezone.utc)+timedelta(minutes=90)).isoformat()
    assert m.patch('/api/appointments/synthetic-visit-000000',json={'status':'confirmed','confirmation_recorded':True,'starts_at':changed,'minutes':20}).status_code==200
    with setup() as db:generate(db);db.commit()
    after=c.get('/api/focus-calendar/notifications/page').json()['items']
    assert len(after)==2 and old not in [r['key'] for r in after]
    assert m.patch('/api/appointments/synthetic-visit-000000',json={'status':'cancelled'}).status_code==200
    assert c.get('/api/focus-calendar/notifications/page').json()['total']==1

@pytest.mark.parametrize('phone_zone',['Pacific/Honolulu','Asia/Tokyo'])
def test_explicit_business_timezone_is_independent_of_phone_zone(setup,monkeypatch,phone_zone):
    monkeypatch.setenv('TZ',phone_zone)
    with setup() as db:seed(db,1,owners=('rep1',))
    c=client('rep1');r=c.post('/api/focus-calendar/tasks',json={'salon_id':'synthetic-salon-000000','title':'DSToffset','due_at':'2027-10-31T09:30:00+09:00'})
    assert r.status_code==201 and r.json()['due_at']=='2027-10-31T00:30:00+00:00'
    result=c.get('/api/focus-calendar/tasks/page?from_date=2027-10-31&to_date=2027-10-31').json()
    assert result['total']==1

def test_parallel_batch_writers_preserve_read_state_and_event_identity(setup):
    with setup() as db:seed(db,505,owners=('rep1',))
    def work(_):
        with setup() as db:n=generate(db);db.commit();return n
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(work,range(2)))
    for _ in range(3):work(0)
    with setup() as db:
        assert db.scalar(select(func.count()).select_from(Notification))==1010
        n=db.scalar(select(Notification).limit(1));key=n.key;at=n.at;n.read=1;db.commit()
    work(0)
    with setup() as db:
        n=db.get(Notification,key);assert n.read==1 and n.at==at

def test_retention_uses_completion_age_not_client_or_task_creation_age(setup):
    with setup() as db:
        seed(db,2,owners=('rep1',))
        first=db.get(Task,'synthetic-task-000000');first.status='completed';first.created_at='2020-01-01T00:00:00+00:00';first.completed_at=datetime.now(timezone.utc).isoformat()
        second=db.get(Task,'synthetic-task-000001');second.status='completed';second.created_at=(datetime.now(timezone.utc)-timedelta(days=400)).isoformat();second.completed_at=(datetime.now(timezone.utc)-timedelta(days=366)).isoformat()
        db.commit()
    result=client().get('/api/focus-calendar/retention-preview').json()
    assert result['candidates']['tasks_for_archive_review']==1 and result['dry_run']

def test_zero_minute_visit_reminder_catches_backlog_without_repeating(setup):
    from backend.native_models import WorkSettings
    with setup() as db:
        seed(db,1,owners=('rep1',))
        db.add(WorkSettings(user_id='rep1',intervals='{"A+":7,"A":14,"B":30,"C":60}',reminders='[0]'))
        a=db.get(Appointment,'synthetic-visit-000000');a.starts_at=(datetime.now(timezone.utc)-timedelta(minutes=20)).isoformat();db.commit()
        assert generate(db)==2;db.commit();assert generate(db)==0;db.commit()
    page=client('rep1').get('/api/focus-calendar/notifications/page').json()
    assert page['total']==2 and any(r['title'].startswith('Termin wizyty:') for r in page['items'])
