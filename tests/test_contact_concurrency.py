"""Real transaction contention on the isolated CI PostgreSQL only."""
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select
from tests.test_api import clean, client, add
from backend.db import Session, engine, User, Job, Activity
from backend.meta_models import MetaConversation
from backend.contact_guard import lock_contact
from backend.worker import authorized_salon


@pytest.mark.parametrize('optout_first',[True,False])
def test_optout_and_worker_commit_are_serialized(optout_first):
    if engine.dialect.name!='postgresql':pytest.skip('Requires isolated PostgreSQL')
    salon=add(client())
    with Session() as db:
        db.add(MetaConversation(id='synthetic-conversation',account_id='synthetic-account',peer_id='synthetic-peer',salon_id=salon['id']))
        db.commit()
    held=threading.Event();attempting=threading.Event();release=threading.Event();completed=threading.Event()
    def action(is_optout,first):
        with Session() as db:
            if not first:
                assert held.wait(5)
                attempting.set()
            lock_contact(db,salon['id'])
            if first:
                held.set()
                assert release.wait(5)
            if is_optout:
                c=db.get(MetaConversation,'synthetic-conversation');c.opted_out=1
            else:
                from types import SimpleNamespace
                job=SimpleNamespace(user_id='manager',salon_id=salon['id'])
                if optout_first:
                    with pytest.raises(ValueError):authorized_salon(db,job,final=True)
                else:
                    authorized_salon(db,job,final=True)
                    db.add(Activity(id='synthetic-draft',salon_id=salon['id'],user_id='manager',kind='agent_draft',body='synthetic'))
            db.commit()
        if not first:completed.set()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(action,optout_first,True)
        second=pool.submit(action,not optout_first,False)
        try:
            assert attempting.wait(5)
            assert not completed.wait(.2)
        finally:release.set()
        first.result(timeout=10);second.result(timeout=10)
    with Session() as db:
        assert db.get(MetaConversation,'synthetic-conversation').opted_out==1
        assert (db.get(Activity,'synthetic-draft') is None)==optout_first


def test_real_optout_and_bind_paths_take_contact_guard(monkeypatch):
    from backend import contact_guard
    from backend.meta_inbox import apply_payload
    from tests.test_meta import event
    from cryptography.fernet import Fernet
    monkeypatch.setenv('META_ENABLED','true')
    monkeypatch.setenv('META_TEST_ACCOUNT_ID','90001')
    monkeypatch.setenv('META_ENCRYPTION_KEY',Fernet.generate_key().decode())
    c=client();salon=add(c)
    with Session() as db:
        db.add(MetaConversation(id='synthetic-bound',account_id='90001',peer_id='90002'))
        db.commit()
    calls=[]
    original=contact_guard.lock_contact
    def track(db,id):
        calls.append(id)
        return original(db,id)
    monkeypatch.setattr(contact_guard,'lock_contact',track)
    # require_config also requires the same synthetic application fields as fixture.
    assert c.post('/api/meta/conversations/synthetic-bound/bind',json={'salon_id':salon['id']}).status_code==200
    with Session() as db:
        apply_payload(db,event(text='STOP'))
        db.commit()
        assert db.get(MetaConversation,'synthetic-bound').opted_out==1
    assert calls == [salon['id'],salon['id']]

from tests.test_meta import configure
