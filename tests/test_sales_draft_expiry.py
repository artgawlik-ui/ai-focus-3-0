"""Seven-day first-contact draft renewal on synthetic PostgreSQL only."""
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import uuid,pytest
from sqlalchemy import select
from tests.test_sales_workflow import isolated,setup,flags,prepared,event
from tests.test_api import client
from backend.db import Activity


def age_draft(factory,draft,days=8):
    with factory() as db:
        db.get(Activity,draft['id']).created_at=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        db.commit()


def test_eight_day_unsent_draft_can_be_renewed_without_losing_history(setup):
    c=client();s,b,old=prepared(c)
    request_id=str(uuid.uuid4())
    not_sent=event(c,b,old,'not_sent',request_id=request_id)
    assert not_sent.status_code==200
    age_draft(setup,old)
    assert event(c,b,old,'manual_sent').status_code==409
    history=c.get(b+'/instagram-contact').json()['events']
    refreshed=c.post(b+'/prepare-instagram')
    assert refreshed.status_code==201
    new=refreshed.json()
    assert new['id']!=old['id'], 'Expired unsent draft must not be reused forever'
    with setup() as db:
        assert len(list(db.scalars(select(Activity).where(Activity.kind=='sales_draft'))))==2
    after=c.get(b+'/instagram-contact').json()['events']
    assert all(item in after for item in history)
    assert event(c,b,old,'not_sent',request_id=request_id).json()['id']==not_sent.json()['id']
    assert c.post(b+'/prepare-instagram').json()['id']==new['id']
    assert event(c,b,new,'manual_sent').status_code==200


@pytest.mark.parametrize('delta,expired',[
    (timedelta(days=7)-timedelta(microseconds=1),False),
    (timedelta(days=7),False),
    (timedelta(days=7)+timedelta(microseconds=1),True),
])
def test_prepare_and_manual_confirmation_agree_at_seven_day_boundary(setup,monkeypatch,delta,expired):
    from backend import sales_workflow
    c=client();s,b,old=prepared(c);at=datetime.now(timezone.utc)
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls,tz=None):return at if tz else at.replace(tzinfo=None)
    monkeypatch.setattr(sales_workflow,'datetime',FrozenDateTime)
    with setup() as db:
        db.get(Activity,old['id']).created_at=(at-delta).isoformat();db.commit()
    current=c.post(b+'/prepare-instagram').json()
    assert (current['id']!=old['id']) is expired
    assert event(c,b,old,'manual_sent').status_code==(409 if expired else 200)
    if expired:assert event(c,b,current,'manual_sent').status_code==200
    assert c.post(b+'/prepare-instagram').status_code==409


@pytest.mark.parametrize('not_sent',[False,True])
def test_parallel_renewal_produces_one_new_draft_and_keeps_old_payload(setup,not_sent):
    c=client();other=client();s,b,old=prepared(c)
    if not_sent:assert event(c,b,old,'not_sent').status_code==200
    age_draft(setup,old)
    previous=c.get(b+'/instagram-contact').json()['events']
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(lambda user:user.post(b+'/prepare-instagram'),[c,other]))
    assert [r.status_code for r in responses]==[201,201]
    assert responses[0].json()['id']==responses[1].json()['id']!=old['id']
    with setup() as db:
        assert len(list(db.scalars(select(Activity).where(Activity.kind=='sales_draft'))))==2
    following=c.get(b+'/instagram-contact').json()['events']
    assert all(item in following for item in previous)
    assert event(c,b,old,'manual_sent').status_code==409


@pytest.mark.parametrize('kind',['call','visit','email_received','instagram_manual'])
def test_expiry_never_bypasses_a_previous_actual_contact(setup,kind):
    c=client();s,b,old=prepared(c);age_draft(setup,old)
    with setup() as db:
        db.add(Activity(id=str(uuid.uuid4()),salon_id=s['id'],user_id='manager',kind=kind,body='Syntetyczny zarejestrowany kontakt'));db.commit()
    assert c.post(b+'/prepare-instagram').status_code==409
    with setup() as db:assert len(list(db.scalars(select(Activity).where(Activity.kind=='sales_draft'))))==1


@pytest.mark.parametrize('block',['crm','meta','refusal'])
def test_expiry_never_bypasses_optout_or_refusal(setup,block):
    from backend.db import Salon
    from backend.meta_models import MetaConversation
    c=client();s,b,old=prepared(c)
    if block=='refusal':
        assert event(c,b,old,'manual_sent').status_code==200
        assert event(c,b,old,'refused').status_code==200
    else:
        with setup() as db:
            if block=='crm':db.get(Salon,s['id']).status='do_not_contact'
            else:db.add(MetaConversation(id=str(uuid.uuid4()),account_id='synthetic',peer_id='synthetic-peer',salon_id=s['id'],opted_out=1))
            db.commit()
    age_draft(setup,old)
    assert c.post(b+'/prepare-instagram').status_code==409
    with setup() as db:assert len(list(db.scalars(select(Activity).where(Activity.kind=='sales_draft'))))==1


def test_expired_draft_cannot_skip_profile_reverification(setup):
    from backend.db import Salon
    c=client();s,b,old=prepared(c);age_draft(setup,old)
    with setup() as db:db.get(Salon,s['id']).instagram='changed_identity';db.commit()
    assert c.post(b+'/prepare-instagram').status_code==409
