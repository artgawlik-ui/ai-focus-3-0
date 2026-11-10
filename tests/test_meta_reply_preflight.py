"""Local reply-interface checks; no implementation of an unverified provider contract."""
import os,json,uuid,hashlib,hmac
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest,httpx
from fastapi import HTTPException
from sqlalchemy import select
from tests.test_native_planning import isolated,setup
from tests.test_meta import configure,event
from tests.test_api import client,add
from backend.db import Activity,Salon,User
from backend.meta import seal
from backend.meta_models import MetaMessage,MetaCredential,MetaConversation,MetaWebhookInbox
from backend.meta_reply_preflight import deny_reply_transport

@pytest.fixture(autouse=True)
def reply_config(setup,monkeypatch):
    monkeypatch.setenv('META_REPLY_PREVIEW_ENABLED','true')
    monkeypatch.setenv('META_REPLY_TRANSPORT_ENABLED','false')
    monkeypatch.setenv('META_DM_TRANSPORT_ENABLED','false')
    from backend import meta_inbox
    monkeypatch.setattr(meta_inbox,'Session',setup)

def signed(c,payload,valid=True):
    raw=json.dumps(payload,ensure_ascii=False).encode()
    signature='sha256='+hmac.new(os.environ['META_APP_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
    return c.post('/api/meta/webhook',content=raw,headers={'X-Hub-Signature-256':signature if valid else 'sha256=invalid'})

def seed(factory):
    c=client();rep=client('rep1');salon=add(rep,instagram='synthetic_customer',specialization='Koloryzacja')
    with factory() as db:
        db.add(MetaCredential(account_id='90001',business_id='fixture',subject_id='fixture',username='artur_uluru_hair',config_id='synthetic-config',token_ciphertext=seal('token','synthetic-token'),expires_at='',checked_at=datetime.now(timezone.utc).isoformat()));db.commit()
    payload=event('reply-fixture','Proszę o wizytę — syntetyczne zapytanie klienta')
    assert signed(c,payload).status_code==200
    from backend.meta_inbox import drain_once
    assert drain_once()==1
    convo=c.get('/api/meta/conversations').json()[0]
    assert c.post('/api/meta/conversations/'+convo['id']+'/bind',json={'salon_id':salon['id']}).status_code==200
    draft=c.post('/api/meta/conversations/'+convo['id']+'/drafts',json={'text':'Dziękuję za zapytanie. Reprezentuję NAK Hair i muk Haircare; proponuję wizytę 15–20 minut.'})
    assert draft.status_code==201
    return c,salon,convo,draft.json(),payload

def review(c,d,**payload):return c.post('/api/meta/replies/'+d['id']+'/check',json=payload)

def test_processed_signed_inbound_is_reviewable_but_never_sendable(setup,caplog):
    c,s,v,d,p=seed(setup)
    result=review(c,d);assert result.status_code==200,result.text
    data=result.json();assert data['inbound_provenance']=='processed_webhook'
    assert not data['can_send'] and not data['transport_implemented'] and not data['owner_api_approval']
    assert set(data['blocking_reasons'])=={'official_contract_unverified','provider_authorization_unverified','reply_window_unverified','api_approval_missing'}
    with setup() as db:
        before=(list(db.scalars(select(MetaMessage.status))),len(list(db.scalars(select(Activity)))))
    assert c.post('/api/meta/messages/'+d['id']+'/approve').status_code==200
    again=review(c,d,expected_fingerprint=data['review_fingerprint']).json()
    assert 'review_stale' in again['blocking_reasons'] and not again['owner_api_approval']
    with setup() as db:
        assert db.get(MetaMessage,d['id']).status=='approved'
        assert not list(db.scalars(select(MetaMessage).where(MetaMessage.status.in_(('pending','api_confirmed_sent')))))
    output=json.dumps(data)+caplog.text
    for secret in ('synthetic-token',os.environ['META_APP_SECRET'],os.environ['META_ENCRYPTION_KEY']):assert secret not in output
    assert 'body_ciphertext' not in data and 'peer_id' not in data

@pytest.mark.parametrize('flag',[None,'','invalid','false','1'])
def test_preview_flag_defaults_off(setup,monkeypatch,flag):
    c,s,v,d,p=seed(setup)
    if flag is None:monkeypatch.delenv('META_REPLY_PREVIEW_ENABLED',raising=False)
    else:monkeypatch.setenv('META_REPLY_PREVIEW_ENABLED',flag)
    assert review(c,d).status_code==404
    assert c.get('/api/meta/replies/status').json()['can_send'] is False

@pytest.mark.parametrize('value',[None,'','invalid','false','1','true'])
def test_transport_is_unreachable_even_if_every_flag_is_requested(monkeypatch,value):
    monkeypatch.setenv('META_ENABLED','true');monkeypatch.setenv('META_DM_TRANSPORT_ENABLED','true')
    if value is None:monkeypatch.delenv('META_REPLY_TRANSPORT_ENABLED',raising=False)
    else:monkeypatch.setenv('META_REPLY_TRANSPORT_ENABLED',value)
    calls=[]
    def forbidden(*args,**kwargs):calls.append(True);raise AssertionError('No provider client may be constructed')
    monkeypatch.setattr(httpx,'Client',forbidden);monkeypatch.setattr(httpx,'post',forbidden)
    with pytest.raises(HTTPException) as result:deny_reply_transport('synthetic-message')
    assert result.value.status_code==(501 if value=='true' else 403)
    assert calls==[]

def test_missing_inbound_and_aggregate_timestamp_never_authorize(setup):
    c,s,v,d,p=seed(setup)
    with setup() as db:
        db.get(MetaConversation,v['id']).last_inbound_at=datetime.now(timezone.utc).isoformat()
        received=db.scalar(select(MetaMessage).where(MetaMessage.direction=='inbound'));received.status='deleted';db.commit()
    data=review(c,d).json();assert 'trusted_inbound_missing' in data['blocking_reasons'] and not data['can_send']

@pytest.mark.parametrize('age',[timedelta(hours=24)-timedelta(seconds=1),timedelta(hours=24),timedelta(hours=24)+timedelta(seconds=1)])
def test_age_is_metadata_not_an_invented_authorized_window(setup,age):
    c,s,v,d,p=seed(setup)
    with setup() as db:
        db.scalar(select(MetaMessage).where(MetaMessage.direction=='inbound')).occurred_at=(datetime.now(timezone.utc)-age).isoformat();db.commit()
    data=review(c,d).json()
    assert abs(data['inbound_age_seconds']-age.total_seconds())<3
    assert 'reply_window_unverified' in data['blocking_reasons'] and data['can_send'] is False

@pytest.mark.parametrize('change',['peer','account','owner','content','optout','token'])
def test_recheck_detects_changes_after_manual_approval(setup,change):
    c,s,v,d,p=seed(setup)
    assert c.post('/api/meta/messages/'+d['id']+'/approve').status_code==200
    before=review(c,d).json()
    with setup() as db:
        if change=='peer':db.get(MetaConversation,v['id']).peer_id='different-peer'
        if change=='account':db.get(MetaConversation,v['id']).account_id='different-account'
        if change=='owner':db.get(Salon,s['id']).owner_id='rep2'
        if change=='content':db.get(MetaMessage,d['id']).body_ciphertext=seal('message','Zmieniony szkic')
        if change=='optout':db.get(Salon,s['id']).status='do_not_contact'
        if change=='token':db.get(MetaCredential,'90001').token_ciphertext=seal('token','new-synthetic-token')
        db.commit()
    after=review(c,d,expected_fingerprint=before['review_fingerprint']).json()
    assert 'review_stale' in after['blocking_reasons'] and not after['can_send']
    if change=='peer':assert 'trusted_inbound_missing' in after['blocking_reasons']
    if change=='account':assert 'account_mismatch' in after['blocking_reasons']
    if change=='optout':assert 'contact_blocked' in after['blocking_reasons']

@pytest.mark.parametrize('change',['expired','revoked','wrong_account','bad_cipher','inactive_owner','meta_optout'])
def test_local_safety_failures_are_explicit(setup,change):
    c,s,v,d,p=seed(setup)
    with setup() as db:
        credential=db.get(MetaCredential,'90001')
        if change=='expired':credential.expires_at='2000-01-01T00:00:00+00:00'
        if change=='revoked':credential.revoked=1
        if change=='wrong_account':credential.username='another_account'
        if change=='bad_cipher':credential.token_ciphertext='not-a-token-cipher'
        if change=='inactive_owner':db.get(User,'rep1').active=0
        if change=='meta_optout':db.get(MetaConversation,v['id']).opted_out=1
        db.commit()
    expected={'expired':'credential_expired','revoked':'credential_unavailable','wrong_account':'target_account_unverified','bad_cipher':'credential_unavailable','inactive_owner':'representative_inactive','meta_optout':'contact_blocked'}
    assert expected[change] in review(c,d).json()['blocking_reasons']


def test_rbac_csrf_and_no_client_recipient_override(setup):
    c,s,v,d,p=seed(setup)
    assert review(client('rep1'),d).status_code==403
    assert review(client('rep2'),d).status_code==403
    assert review(c,d,peer_id='https://www.instagram.com/other/').status_code==422
    assert c.post('/api/meta/replies/'+d['id']+'/check',json={},headers={'X-CSRF-Token':''}).status_code==403
    assert c.post('/api/meta/replies/'+d['id']+'/send',json={}).status_code in (404,405)


def test_parallel_checks_do_not_approve_or_create_attempts(setup):
    c,s,v,d,p=seed(setup);second=client()
    with setup() as db:before=len(list(db.scalars(select(Activity))))
    with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda user:review(user,d).json(),[c,second]))
    assert results[0]['review_fingerprint']==results[1]['review_fingerprint']
    assert all(r['can_send'] is False for r in results)
    with setup() as db:
        assert db.get(MetaMessage,d['id']).status=='draft'
        assert len(list(db.scalars(select(Activity))))==before


def test_signature_and_replay_are_still_enforced(setup):
    c,s,v,d,p=seed(setup)
    assert signed(c,event('forged'),valid=False).status_code==403
    assert signed(c,p).status_code==200
    from backend.meta_inbox import drain_once
    drain_once()
    with setup() as db:
        assert len(list(db.scalars(select(MetaMessage).where(MetaMessage.direction=='inbound'))))==1
        assert len(list(db.scalars(select(MetaWebhookInbox))))==1
    assert review(c,d).json()['inbound_provenance']=='processed_webhook'
