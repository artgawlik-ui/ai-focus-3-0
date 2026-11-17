from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import pytest
from sqlalchemy import select
from tests.test_api import clean,client,add
from backend.db import Session,Appointment,Activity,engine

@pytest.fixture(autouse=True)
def planner(monkeypatch):monkeypatch.setenv('VISIT_PLANNER_ENABLED','true')


def create(c,salon,start='2027-03-29T10:00:00+02:00',**kw):
    return c.post('/api/appointments',json={'salon_id':salon['id'],'starts_at':start,'minutes':20,**kw})


def test_proposal_history_and_calendar_preview_have_no_external_write():
    c=client();s=add(c,address='Syntetyczna 1');r=create(c,s);assert r.status_code==201
    v=r.json();assert v['status']=='proposed'
    assert c.get('/api/appointments?day=2027-03-29').json()[0]['address_verified'] is False
    preview=c.get('/api/appointments/'+v['id']+'/calendar-preview').json()
    assert preview['external_write'] is False and preview['connected'] is False
    assert preview['event']['status']=='tentative' and 'location' not in preview['event']
    assert c.get('/api/routes?day=2027-03-29').json()['url'] is None
    assert any(a['kind']=='appointment' for a in c.get('/api/salons/'+s['id']+'/activities').json())


def test_explicit_confirmation_and_duplicate_conflict():
    c=client();s=add(c)
    assert create(c,s,status='confirmed').status_code==422
    r=create(c,s,status='confirmed',confirmation_recorded=True);assert r.status_code==201
    assert create(c,s).status_code==409


def test_week_rep_rbac_and_dst_boundaries():
    a,b,m=client('rep1'),client('rep2'),client()
    s=add(a);s2=add(b,name='Syntetyczny drugi')
    assert create(a,s,start='2027-03-28T00:15:00+01:00').status_code==201
    assert create(b,s2,start='2027-03-29T10:00:00+02:00').status_code==201
    assert len(m.get('/api/appointments?day=2027-03-28&days=7').json())==2
    assert len(a.get('/api/appointments?day=2027-03-28&days=7').json())==1
    assert a.get('/api/appointments?representative_id=rep2').status_code==403
    assert len(m.get('/api/appointments?representative_id=rep2').json())==1
    assert a.get('/api/appointments?days=8').status_code==422


def test_reschedule_cancel_and_stale_revision():
    c=client();s=add(c);v=create(c,s).json()
    row=c.get('/api/appointments?day=2027-03-29').json()[0]
    patch={'status':'proposed','starts_at':'2027-03-30T11:00:00+02:00','minutes':15,'notes':'Zmieniono syntetyczny termin','expected_revision':row['revision']}
    assert c.patch('/api/appointments/'+v['id'],json=patch).status_code==200
    assert c.patch('/api/appointments/'+v['id'],json=patch).status_code==409
    assert c.get('/api/appointments?day=2027-03-29').json()==[]
    updated=c.get('/api/appointments?day=2027-03-30').json()[0]
    assert updated['notes']==patch['notes']
    assert c.patch('/api/appointments/'+v['id'],json={'status':'cancelled','expected_revision':updated['revision']}).status_code==200
    assert create(c,s,start=patch['starts_at']).status_code==201


def test_collision_on_reschedule_and_status_reactivation():
    c=client();s=add(c);a=create(c,s).json();b=create(c,s,start='2027-03-29T11:00:00+02:00').json()
    assert c.patch('/api/appointments/'+b['id'],json={'status':'proposed','starts_at':a['starts_at']}).status_code==409
    assert c.patch('/api/appointments/'+a['id'],json={'status':'cancelled'}).status_code==200
    assert c.patch('/api/appointments/'+b['id'],json={'status':'proposed','starts_at':a['starts_at']}).status_code==200
    assert c.patch('/api/appointments/'+a['id'],json={'status':'proposed'}).status_code==409


def test_verified_address_is_invalidated_after_profile_change():
    c=client();s=add(c,address='Syntetyczna 1');v=create(c,s,status='confirmed',confirmation_recorded=True).json()
    assert c.get('/api/routes?day=2027-03-29').json()['url'] is None
    assert c.post('/api/salons/'+s['id']+'/verify-address',json={'address':'Nieaktualny','city':s['city']}).status_code==409
    assert c.post('/api/salons/'+s['id']+'/verify-address',json={'address':s['address'],'city':s['city']}).status_code==200
    assert c.get('/api/routes?day=2027-03-29').json()['url']
    assert 'location' in c.get('/api/appointments/'+v['id']+'/calendar-preview').json()['event']
    data={k:s[k] for k in __import__('backend.schemas',fromlist=['SalonUpdate']).SalonUpdate.model_fields};data['address']='Syntetyczna 2'
    assert c.put('/api/salons/'+s['id'],json=data).status_code==200
    assert c.get('/api/routes?day=2027-03-29').json()['url'] is None


def test_other_sales_cannot_update_view_preview_or_verify():
    a,b=client('rep1'),client('rep2');s=add(a,address='Syntetyczna 1');v=create(a,s).json()
    assert b.patch('/api/appointments/'+v['id'],json={'status':'cancelled'}).status_code==404
    assert b.get('/api/appointments/'+v['id']+'/calendar-preview').status_code==404
    assert b.post('/api/salons/'+s['id']+'/verify-address',json={'address':s['address'],'city':s['city']}).status_code==404


def test_parallel_same_slot_has_one_winner():
    if engine.dialect.name!='postgresql':pytest.skip('Requires isolated PostgreSQL')
    c=client();s=add(c)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:create(c,s).status_code,range(2)))
    assert sorted(results)==[201,409]
    with Session() as db:assert len(list(db.scalars(select(Appointment))))==1


@pytest.mark.parametrize('start,minutes',[('2027-03-29T10:00:00',20),('2027-03-29T10:00:00Z',14)])
def test_invalid_time_or_duration(start,minutes):
    c=client();s=add(c)
    assert create(c,s,start=start,minutes=minutes).status_code==422


def test_calendar_cancel_preview_stable_id_and_no_http(monkeypatch):
    import httpx
    def forbidden(*_):raise AssertionError('External transport forbidden')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',forbidden)
    c=client();s=add(c);v=create(c,s).json()
    first=c.get('/api/appointments/'+v['id']+'/calendar-preview').json()['event']
    assert c.patch('/api/appointments/'+v['id'],json={'status':'cancelled'}).status_code==200
    after=c.get('/api/appointments/'+v['id']+'/calendar-preview').json()['event']
    assert first['id']==after['id'] and after['status']=='cancelled'
    assert not c.get('/api/appointments?day=2027-03-29').json()[0]['google_calendar_url']


def test_planner_off_preserves_legacy_but_blocks_rescheduling(monkeypatch):
    monkeypatch.setenv('VISIT_PLANNER_ENABLED','false')
    c=client();s=add(c);v=create(c,s).json()
    assert c.patch('/api/appointments/'+v['id'],json={'status':'proposed','minutes':15}).status_code==404
    assert c.patch('/api/appointments/'+v['id'],json={'status':'cancelled'}).status_code==200


def test_optout_blocks_proposal_but_not_cancellation():
    from backend.meta_models import MetaConversation
    c=client();s=add(c);v=create(c,s).json()
    with Session() as db:
        db.add(MetaConversation(id='synthetic-stop',account_id='synthetic-account',peer_id='synthetic-peer',salon_id=s['id'],opted_out=1));db.commit()
    assert create(c,s,start='2027-03-30T10:00:00+02:00').status_code==409
    assert c.patch('/api/appointments/'+v['id'],json={'status':'confirmed','confirmation_recorded':True}).status_code==409
    assert c.patch('/api/appointments/'+v['id'],json={'status':'cancelled'}).status_code==200


def test_stale_note_revision_does_not_overwrite_newer_note():
    c=client();s=add(c);v=create(c,s).json()
    row=c.get('/api/appointments?day=2027-03-29').json()[0]
    assert c.patch('/api/appointments/'+v['id'],json={'status':'proposed','notes':'Pierwsza zmiana','expected_revision':row['revision']}).status_code==200
    assert c.patch('/api/appointments/'+v['id'],json={'status':'proposed','notes':'Stara zmiana','expected_revision':row['revision']}).status_code==409


def test_sales_proposes_manager_confirms_with_explicit_attestation():
    a,m=client('rep1'),client();s=add(a);v=create(a,s).json()
    assert create(a,s,start='2027-03-30T10:00:00+02:00',status='confirmed',confirmation_recorded=True).status_code==403
    assert a.patch('/api/appointments/'+v['id'],json={'status':'confirmed','confirmation_recorded':True}).status_code==403
    assert m.patch('/api/appointments/'+v['id'],json={'status':'confirmed','confirmation_recorded':True}).status_code==200


def test_manager_route_does_not_mix_salespeople():
    a,b,m=client('rep1'),client('rep2'),client()
    for c,name in [(a,'Syntetyczny pierwszy'),(b,'Syntetyczny drugi')]:
        s=add(c,name=name,address='Syntetyczna 1')
        assert c.post('/api/salons/'+s['id']+'/verify-address',json={'address':s['address'],'city':s['city']}).status_code==200
        assert create(m,s,status='confirmed',confirmation_recorded=True).status_code==201
    assert m.get('/api/routes?day=2027-03-29').json()['url'] is None
    assert m.get('/api/routes?day=2027-03-29&representative_id=rep1').json()['url']
