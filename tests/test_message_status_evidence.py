"""Signed synthetic webhook evidence; no Meta transport or real contacts."""
from copy import deepcopy

import pytest
from sqlalchemy import select

from tests.test_api import clean, client, add
from tests.test_meta import configure, event, webhook, cid
from backend.db import Session, Activity
from backend.meta_models import MetaMessage
from backend.meta_inbox import apply_payload


@pytest.mark.parametrize('value', ['false', 'true', 0, 1, None, {}, []])
def test_non_boolean_deletion_cannot_erase_existing_message(value):
    owner = client()
    assert webhook(owner, event()).status_code == 200
    conversation = cid(owner)
    malformed = event(is_deleted=value)
    assert webhook(owner, malformed).status_code == 200
    # Old durable inbox rows must be guarded too, even if they predate validation.
    with Session() as db:
        apply_payload(db, malformed)
        db.commit()
    messages = owner.get('/api/meta/conversations/'+conversation+'/messages').json()
    assert len(messages) == 1
    assert messages[0]['status'] == 'received'
    assert messages[0]['text'] == 'Proszę o termin wizyty'
    # Rejected evidence cannot consume the dedup key of a later valid deletion.
    assert webhook(owner, event(is_deleted=True)).status_code == 200
    assert owner.get('/api/meta/conversations/'+conversation+'/messages').json()[0]['status'] == 'deleted'


def test_echo_from_peer_cannot_create_inbound_reply_or_crm_activity():
    owner = client()
    salon = add(owner)
    assert webhook(owner, event()).status_code == 200
    conversation = cid(owner)
    assert owner.post('/api/meta/conversations/'+conversation+'/bind',
                      json={'salon_id': salon['id']}).status_code == 200
    before = owner.get('/api/meta/conversations').json()[0]
    with Session() as db:
        activities = len(list(db.scalars(select(Activity))))
    assert webhook(owner, event('invalid-echo', is_echo=True)).status_code == 200
    messages = owner.get('/api/meta/conversations/'+conversation+'/messages').json()
    assert len(messages) == 1
    assert owner.get('/api/meta/conversations').json()[0] == before
    with Session() as db:
        apply_payload(db, event('invalid-echo', is_echo=True))
        db.commit()
        assert len(list(db.scalars(select(Activity)))) == activities
        assert not db.scalar(select(MetaMessage).where(MetaMessage.external_id=='invalid-echo'))
    echo = event('invalid-echo', is_echo=True)
    item = echo['entry'][0]['messaging'][0]
    item['sender']['id'], item['recipient']['id'] = '90001', '90002'
    assert webhook(owner, echo).status_code == 200
    messages = owner.get('/api/meta/conversations/'+conversation+'/messages').json()
    assert {row['status'] for row in messages} == {'received','api_confirmed_sent'}


@pytest.mark.parametrize('value', ['false', 'true', 0, 1, None, {}, []])
def test_non_boolean_echo_cannot_create_an_inbound_message(value):
    owner = client()
    assert webhook(owner, event(is_echo=value)).status_code == 200
    assert owner.get('/api/meta/conversations').json() == []
    with Session() as db:
        assert not list(db.scalars(select(MetaMessage)))


def test_valid_inbound_echo_and_deletion_keep_distinct_statuses():
    owner = client()
    assert webhook(owner, event(is_echo=False, is_deleted=False)).status_code == 200
    conversation = cid(owner)
    echo = deepcopy(event('confirmed-echo', is_echo=True, is_deleted=False))
    item = echo['entry'][0]['messaging'][0]
    item['sender']['id'], item['recipient']['id'] = '90001', '90002'
    assert webhook(owner, echo).status_code == 200
    messages = owner.get('/api/meta/conversations/'+conversation+'/messages').json()
    states = {row['status'] for row in messages}
    assert states == {'received', 'api_confirmed_sent'}
    assert webhook(owner, event(is_deleted=True)).status_code == 200
    messages = owner.get('/api/meta/conversations/'+conversation+'/messages').json()
    assert {row['status'] for row in messages} == {'deleted', 'api_confirmed_sent'}
    assert next(row for row in messages if row['status']=='deleted')['text'] == ''
