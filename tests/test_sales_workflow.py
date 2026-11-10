"""Real PostgreSQL transactions; synthetic accounts, no outbound network."""
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select
from tests.test_native_planning import isolated,setup
from tests.test_api import client,add
from backend.db import Activity,Salon
from backend.native_models import Task
from backend.sales_workflow import handle

@pytest.fixture(autouse=True)
def flags(monkeypatch,setup):
    monkeypatch.setenv('SALES_WORKFLOW_ENABLED','true');monkeypatch.setenv('BOOTSTRAP_EMAIL','manager@focus.test')

def prepared(c,name='Fikcyjny salon'):
    s=add(c,name,instagram='@synthetic_salon',specialization='koloryzacja',source_url='https://www.openstreetmap.org/node/900000000001',potential=4000,stage='offer')
    base='/api/salons/'+s['id']
    assert c.post(base+'/verify-instagram',json={'profile':'synthetic_salon','identity_confirmed':True,'evidence':'Syntetyczne potwierdzenie profilu'}).status_code==200
    r=c.post(base+'/prepare-instagram');assert r.status_code==201,r.text
    return s,base,r.json()
def event(c,b,d,action,**kw):
    return c.post(b+'/instagram-events',json={'draft_id':d['id'],'action':action,'request_id':str(uuid.uuid4()),'confirmed':True,'note':'Syntetyczny wynik kontaktu',**kw})

@pytest.mark.parametrize('bad',['https://evil.invalid/test','https://www.instagram.com/direct/inbox','x?token=foo','@bad/name','https://www.instagram.com/good/?x=1','a..b'])
def test_invalid_profile(bad):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):handle(bad)

def test_full_contact_task_report_and_no_fake_receipt(setup):
    c=client('rep1');s,b,d=prepared(c)
    assert d['details']['priority']=='A+'
    text=d['details']['text'];assert 'NAK Hair' in text and 'muk Haircare' in text and 'koloryzacja' in text and '15–20' in text
    assert c.post(b+'/prepare-instagram').json()['id']==d['id']
    assert c.get('/api/focus-calendar/contacts').json()[0]['last_contact_at'] is None
    assert event(c,b,d,'manual_sent').status_code==403
    m=client();assert event(m,b,d,'manual_sent').status_code==200
    assert c.get('/api/focus-calendar/contacts').json()[0]['days_since_contact']==0
    assert event(c,b,d,'replied',customer_initiated=True).status_code==200
    with setup() as db:
        assert db.scalar(select(Salon.stage).where(Salon.id==s['id']))=='offer' # Preserve an existing later funnel stage.
        assert len(list(db.scalars(select(Task).where(Task.cycle_key.like('sales-reply:%')))))==1
    assert c.get(b+'/instagram-contact').json()['api_confirmed_sent'] is False
    assert c.get('/api/focus-calendar/report').status_code==200
    assert c.post(b+'/prepare-instagram').status_code==409

def test_two_sessions_idempotency_and_distinct_requests(setup):
    c=client();s,b,d=prepared(c);other=client()
    rid=str(uuid.uuid4())
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda x:event(x,b,d,'manual_sent',request_id=rid),[c,other]))
    assert [r.status_code for r in results]==[200,200]
    assert results[0].json()['id']==results[1].json()['id']
    assert event(other,b,d,'manual_sent').status_code==409
    with setup() as db:assert len(list(db.scalars(select(Activity).where(Activity.kind=='instagram_manual'))))==1

def test_rbac_optout_and_no_send_without_confirmation(setup):
    c=client('rep1');s,b,d=prepared(c);m=client();outsider=client('rep2')
    assert outsider.get(b+'/instagram-contact').status_code==404
    assert event(outsider,b,d,'manual_sent').status_code==404
    assert event(m,b,d,'manual_sent',confirmed=False).status_code==422
    assert event(m,b,d,'manual_sent').status_code==200
    assert event(c,b,d,'refused').status_code==200
    assert c.get('/api/salons/'+s['id']).json()['status']=='do_not_contact'
    assert c.post('/api/agent/jobs',json={'salon_id':s['id']}).status_code==409
    assert event(m,b,d,'manual_sent').status_code==409
    assert c.post(b+'/prepare-instagram').status_code==409

def test_profile_mismatch_stale_and_prior_contact(setup):
    c=client();s,b,d=prepared(c)
    assert c.post(b+'/verify-instagram',json={'profile':'wrong_profile','identity_confirmed':True,'evidence':'Fikcyjne potwierdzenie'}).status_code==409
    with setup() as db:db.get(Salon,s['id']).instagram='changed_profile';db.commit()
    assert not c.get(b+'/instagram-contact').json()['profile_verified']
    assert event(c,b,d,'manual_sent').status_code==409

def test_other_channel_contact_after_draft_blocks(setup):
    c=client();s,b,d=prepared(c)
    c.post(b+'/activities',json={'kind':'call','body':'Rzeczywista rozmowa syntetyczna'})
    assert event(c,b,d,'manual_sent').status_code==409
    assert c.post(b+'/prepare-instagram').status_code==409

def test_not_sent_is_not_contact_and_no_meeting_before_initiative(setup):
    c=client();s,b,d=prepared(c)
    assert event(c,b,d,'not_sent').status_code==200
    assert c.get('/api/focus-calendar/contacts').json()[0]['last_contact_at'] is None
    p={'salon_id':s['id'],'starts_at':'2027-02-10T12:00:00+01:00','minutes':20}
    assert c.post('/api/appointments',json=p).status_code==409
    event(c,b,d,'manual_sent');event(c,b,d,'replied',customer_initiated=True)
    assert c.post('/api/appointments',json=p).status_code==201
    assert c.post('/api/appointments',json=p).status_code==409

@pytest.mark.parametrize('value',['','false','nonsense'])
def test_feature_fail_closed(monkeypatch,value):
    c=client();s=add(c);monkeypatch.setenv('SALES_WORKFLOW_ENABLED',value)
    assert c.get('/api/salons/'+s['id']+'/instagram-contact').status_code==404

def test_parallel_distinct_requests_and_reply_dedup(setup):
    c=client();other=client();s,b,d=prepared(c)
    with ThreadPoolExecutor(2) as pool:codes=list(pool.map(lambda x:event(x,b,d,'manual_sent').status_code,[c,other]))
    assert sorted(codes)==[200,409]
    rid=str(uuid.uuid4())
    assert event(c,b,d,'replied',request_id=rid,customer_initiated=True).status_code==200
    assert event(c,b,d,'replied',request_id=rid,customer_initiated=True).status_code==200
    assert event(c,b,d,'replied',request_id=rid,note='Changed payload').status_code==409
    with setup() as db:
        assert len(list(db.scalars(select(Task))))==1
        assert len(list(db.scalars(select(Activity).where(Activity.kind=='instagram_reply_manual'))))==1

def test_profile_click_and_draft_do_not_count_as_contact(setup):
    c=client();s,b,d=prepared(c)
    before=len(c.get(b+'/activities').json())
    for _ in range(2):assert c.get(b+'/instagram-contact').status_code==200
    assert len(c.get(b+'/activities').json())==before
    assert c.get('/api/focus-calendar/report').json()['counts']['contacts_recorded']==0

def test_legacy_meta_audit_is_readable_and_prevents_repeat(setup):
    c=client();s,b,d=prepared(c)
    with setup() as db:
        db.add(Activity(id=str(uuid.uuid4()),salon_id=s['id'],user_id='manager',kind='instagram_manual',body='Właściciel oświadczył wysłanie ręczne; brak potwierdzenia API'));db.commit()
    state=c.get(b+'/instagram-contact');assert state.status_code==200
    assert state.json()['events'][-1]['source']=='legacy_crm_activity'
    assert c.post(b+'/prepare-instagram').status_code==409
    assert event(c,b,d,'manual_sent').status_code==409

def test_sales_flag_does_not_change_team_training(setup):
    c=client();r=c.post('/api/trainings',json={'title':'Syntetyczne szkolenie zespołu','starts_at':'2027-03-12T10:00:00+01:00','minutes':20})
    assert r.status_code==201

def test_meta_optout_blocks_manual_panel_even_with_legacy_crm_status(setup):
    from backend.meta_models import MetaConversation
    c=client();s,b,d=prepared(c)
    with setup() as db:
        db.add(MetaConversation(id=str(uuid.uuid4()),account_id='synthetic',peer_id='synthetic-peer',salon_id=s['id'],opted_out=1));db.commit()
    assert c.get(b+'/instagram-contact').json()['blocked']
    assert c.post(b+'/prepare-instagram').status_code==409
    assert event(c,b,d,'manual_sent').status_code==409

def test_later_withdrawal_after_positive_reply_is_always_recordable(setup):
    c=client();s,b,d=prepared(c)
    assert event(c,b,d,'manual_sent').status_code==200
    assert event(c,b,d,'replied',customer_initiated=True).status_code==200
    assert event(c,b,d,'refused',note='Późniejsze wycofanie zgody — syntetyczne').status_code==200
    assert c.get(b+'/instagram-contact').json()['blocked']
    assert event(c,b,d,'replied',customer_initiated=True).status_code==409
    assert c.post('/api/agent/jobs',json={'salon_id':s['id']}).status_code==409
