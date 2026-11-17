"""Regresja 3.0.4: tylko syntetyczne zdarzenia, bez transportu Meta."""
import json
import pytest
from sqlalchemy import select
from tests.test_api import clean,client
from tests.test_meta import configure,event,webhook,cid
from tests.test_meta_303 import seed_token
from backend.db import Session
from backend.meta_models import MetaWebhookInbox,MetaMessage
from backend.meta_inbox import persist,drain_once,claim_batch,process_claim


def test_unicode_signature_and_verify_token_are_rejected_not_server_errors():
    from fastapi.testclient import TestClient
    from backend.main import app
    c=TestClient(app,raise_server_exceptions=False)
    body=json.dumps(event()).encode()
    assert c.post('/api/meta/webhook',content=body,headers=[(b'x-hub-signature-256',b'sha256=\xff')]).status_code==403
    assert c.get('/api/meta/webhook',params={'hub.mode':'subscribe','hub.verify_token':'nieprawidłowy-ż','hub.challenge':'1'}).status_code==403


def test_unsend_erases_original_encrypted_inbox_copies():
    c=client();seed_token()
    assert webhook(c,event()).status_code==200
    with Session() as db:
        original=db.scalar(select(MetaWebhookInbox));original_id=original.id
        assert original.payload_ciphertext
    assert webhook(c,event(is_deleted=True)).status_code==200
    with Session() as db:
        assert not db.get(MetaWebhookInbox,original_id).payload_ciphertext
        assert db.scalar(select(MetaMessage)).status=='deleted'


def test_delete_before_original_cannot_restore_content_in_inbox():
    c=client();seed_token()
    assert webhook(c,event(is_deleted=True)).status_code==200
    assert webhook(c,event()).status_code==200
    with Session() as db:
        assert db.scalar(select(MetaMessage)).status=='deleted'
        # Retain deletion metadata, but never retain replayed deleted text.
        for row in db.scalars(select(MetaWebhookInbox)):
            if row.payload_ciphertext:
                from backend.meta import unseal
                message=unseal('inbox',row.payload_ciphertext)['entry'][0]['messaging'][0]['message']
                assert message.get('is_deleted')


def test_processor_uses_privacy_lock_order_without_holding_inbox_while_waiting():
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import event as sa_event
    from backend.db import engine
    from backend.meta_models import MetaCredential
    seed_token();persist(event());claim=claim_batch()[0]
    waiting=threading.Event()
    def before_execute(conn,cursor,statement,parameters,context,executemany):
        if threading.current_thread() is not threading.main_thread() and 'meta_credentials' in statement and 'FOR UPDATE' in statement:waiting.set()
    sa_event.listen(engine,'before_cursor_execute',before_execute)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with Session() as db:
                db.scalar(select(MetaCredential).with_for_update())
                future=pool.submit(process_claim,*claim)
                assert waiting.wait(2)
                # Callback prywatności trzyma credential i może bez blokady dostać inbox.
                assert db.scalar(select(MetaWebhookInbox).with_for_update(nowait=True))
                db.rollback()
            assert future.result()
    finally:sa_event.remove(engine,'before_cursor_execute',before_execute)


def test_deleted_pending_original_is_fenced_and_payload_erased():
    seed_token();persist(event());original=claim_batch()[0]
    persist(event(is_deleted=True));deletion=claim_batch()[0]
    assert process_claim(*deletion)
    assert not process_claim(*original)
    with Session() as db:
        for row in db.scalars(select(MetaWebhookInbox)):
            assert row.status=='done'
        assert not db.get(MetaWebhookInbox,original[0]).payload_ciphertext
        assert db.scalar(select(MetaMessage)).status=='deleted'


def test_malformed_sender_does_not_poison_retry_queue():
    payload=event();payload['entry'][0]['messaging'][0]['sender']='malformed'
    persist(payload);assert drain_once()==1
    with Session() as db:
        assert db.scalar(select(MetaWebhookInbox)).status=='done'
        assert not db.scalar(select(MetaMessage))


def test_unsend_has_one_crm_audit_without_content_or_repeated_activity():
    from tests.test_api import add
    from backend.db import Activity
    c=client();seed_token();salon=add(c)
    webhook(c,event());conversation=cid(c)
    c.post('/api/meta/conversations/'+conversation+'/bind',json={'salon_id':salon['id']})
    webhook(c,event(is_deleted=True));webhook(c,event(is_deleted=True));webhook(c,event())
    with Session() as db:
        activities=list(db.scalars(select(Activity).where(Activity.kind=='instagram_deleted')))
        assert len(activities)==1 and 'meta_message:' in activities[0].body
        assert 'Proszę' not in activities[0].body
        assert all(not row.payload_ciphertext for row in db.scalars(select(MetaWebhookInbox)))


@pytest.mark.parametrize('version',['3.0.3','unexpected'])
def test_production_probe_only_uses_get_and_never_authenticates(monkeypatch,version):
    import httpx
    from tests.production_meta_readonly_check import check
    calls=[]
    def handle(request):
        calls.append((request.method,request.url.path))
        path=request.url.path
        code=200 if path in ('/api/health','/manifest.webmanifest','/sw.js') else 404 if path in ('/api/meta/webhook','/api/meta/oauth/callback') else 401
        data={'status':'ok','version':version} if path=='/api/health' else {'display':'standalone'} if path=='/manifest.webmanifest' else {}
        return httpx.Response(code,json=data,headers={'cache-control':'no-store','strict-transport-security':'max-age=31536000','x-content-type-options':'nosniff','x-frame-options':'DENY','content-security-policy':"frame-ancestors 'none'"})
    original=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original(**kwargs,transport=httpx.MockTransport(handle)))
    if version=='unexpected':
        with pytest.raises(AssertionError):check('3.0.3')
    else:assert check('3.0.3')['status']=='PASS'
    assert calls and all(method=='GET' for method,path in calls)
    assert not any(path=='/api/auth/login' for method,path in calls)


def test_opt_out_still_blocks_agent_after_unsend_and_meta_disable(monkeypatch):
    from tests.test_api import add
    from backend.worker import run_once
    c=client();seed_token();salon=add(c)
    webhook(c,event());conversation=cid(c)
    c.post('/api/meta/conversations/'+conversation+'/bind',json={'salon_id':salon['id']})
    assert c.post('/api/agent/jobs',json={'salon_id':salon['id']}).status_code==202
    webhook(c,event('stop-mid','Nie kontaktuj się ponownie'))
    webhook(c,event('stop-mid','Nie kontaktuj się ponownie',is_deleted=True))
    monkeypatch.setenv('META_ENABLED','false')
    assert c.post('/api/agent/jobs',json={'salon_id':salon['id']}).status_code==409
    assert run_once()
    job=c.get('/api/agent/jobs').json()[0]
    assert job['status']=='failed'
    assert not json.loads(job['result']).get('draft')
