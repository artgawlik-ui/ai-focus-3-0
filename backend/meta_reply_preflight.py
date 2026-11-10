"""Local reply safety review only. Official send contract remains unverified.
No provider endpoint/client, send route, durable approval or receipt is implemented.
"""
import hashlib,json,os
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select
from backend.db import Salon,User
from backend.security import current,manager,database
from backend.contact_guard import lock_contact
from backend.meta import require_config,owner,unseal
from backend.meta_models import MetaMessage,MetaConversation,MetaCredential,MetaWebhookInbox

router=APIRouter(prefix='/api/meta/replies',tags=['Lokalny podgląd odpowiedzi — bez wysyłki'])

def preview_enabled():return os.getenv('META_REPLY_PREVIEW_ENABLED','').strip().lower()=='true'
def transport_requested():return os.getenv('META_REPLY_TRANSPORT_ENABLED','').strip().lower()=='true'

def deny_reply_transport(*args,**kwargs):
    # No flag or injected client can enable an unverified transport.
    from backend.meta_flags import dm_enabled
    if not transport_requested() or not dm_enabled():raise HTTPException(403,'Transport odpowiedzi wyłączony')
    raise HTTPException(501,'Kontrakt Meta niezweryfikowany; transport nie istnieje')

@router.get('/status')
def status(user=Depends(current)):
    return {'preview_enabled':preview_enabled(),'contract_status':'blocked','provider_authorization_verified':False,
            'window_policy_verified':False,'transport_implemented':False,'can_send':False}

class ReviewIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_fingerprint:str=Field(default='',max_length=64,pattern=r'^(?:[0-9a-f]{64})?$')

def instant(value):
    try:
        at=datetime.fromisoformat(value.replace('Z','+00:00'))
        return at.astimezone(timezone.utc) if at.tzinfo else None
    except (ValueError,TypeError,AttributeError):return None

def inbox_proves(db,c,inbound):
    # Use the processed inbox, not a username, aggregate timestamp or outbound echo.
    if not inbound or not inbound.external_id:return False
    accounts=[c.account_id]
    if c.account_id.isdecimal():accounts.append(int(c.account_id))
    keys=[hashlib.sha256(json.dumps([a,'message',inbound.external_id],sort_keys=True,separators=(',',':')).encode()).hexdigest() for a in accounts]
    row=db.scalar(select(MetaWebhookInbox).where(MetaWebhookInbox.account_id==c.account_id,MetaWebhookInbox.dedup_key.in_(keys),MetaWebhookInbox.status=='done',MetaWebhookInbox.processed_at!='').limit(1))
    if not row or not row.payload_ciphertext:return False
    try:
        payload=unseal('inbox',row.payload_ciphertext)
        for entry in payload['entry']:
            if str(entry['id'])!=c.account_id:continue
            for event in entry['messaging']:
                m=event['message']
                if (str(event['sender']['id'])==c.peer_id and str(event['recipient']['id'])==c.account_id
                    and m['mid']==inbound.external_id and not m.get('is_echo') and not m.get('is_deleted')
                    and datetime.fromtimestamp(event['timestamp']/1000,timezone.utc)==instant(inbound.occurred_at)):
                    return True
    except (HTTPException,ValueError,TypeError,KeyError,AttributeError,OverflowError,OSError):pass
    return False

@router.post('/{message_id}/check')
def check(message_id:str,payload:ReviewIn,user=Depends(manager),db=Depends(database)):
    owner(user)
    if not preview_enabled():raise HTTPException(404,'Podgląd odpowiedzi wyłączony')
    require_config('crm_history')
    item=db.get(MetaMessage,message_id)
    if not item:raise HTTPException(404,'Szkic niedostępny')
    conversation=db.get(MetaConversation,item.conversation_id)
    if not conversation:raise HTTPException(404,'Rozmowa niedostępna')
    # Follow inbox/privacy lock ordering. No locks are held across network I/O (none exists).
    credential=db.scalar(select(MetaCredential).where(MetaCredential.account_id==conversation.account_id).with_for_update())
    conversation=db.get(MetaConversation,conversation.id,populate_existing=True,with_for_update=True)
    lock_contact(db,conversation.salon_id)
    salon=db.get(Salon,conversation.salon_id,populate_existing=True,with_for_update=True) if conversation.salon_id else None
    item=db.get(MetaMessage,message_id,populate_existing=True,with_for_update=True)
    if not item or item.conversation_id!=conversation.id:raise HTTPException(409,'Rozmowa zmieniona; odczytaj ponownie')
    at=datetime.now(timezone.utc)
    blockers=['official_contract_unverified','provider_authorization_unverified','reply_window_unverified','api_approval_missing']
    actor=db.get(User,user.id,populate_existing=True)
    if not actor or not actor.active:raise HTTPException(403,'Konto nieaktywne')
    owner(actor)
    if conversation.account_id!=os.getenv('META_TEST_ACCOUNT_ID'):blockers.append('account_mismatch')
    if not salon:blockers.append('salon_not_bound')
    else:
        representative=db.get(User,salon.owner_id,populate_existing=True)
        if not representative or not representative.active:blockers.append('representative_inactive')
        if salon.status=='do_not_contact' or conversation.opted_out:blockers.append('contact_blocked')
        if db.scalar(select(MetaConversation.id).where(MetaConversation.salon_id==salon.id,MetaConversation.opted_out==1).limit(1)) and 'contact_blocked' not in blockers:blockers.append('contact_blocked')
    if not credential or credential.revoked or not credential.token_ciphertext:blockers.append('credential_unavailable')
    else:
        expiry=instant(credential.expires_at) if credential.expires_at else None
        if credential.expires_at and (not expiry or expiry<=at):blockers.append('credential_expired')
        if credential.username.casefold()!='artur_uluru_hair':blockers.append('target_account_unverified')
        if credential.config_id!=os.getenv('META_CONFIG_ID') or not credential.subject_id or not credential.business_id:blockers.append('grant_binding_unverified')
        try:
            token=unseal('token',credential.token_ciphertext)
            if not isinstance(token,str) or not token.strip():blockers.append('credential_unavailable')
        except HTTPException:blockers.append('credential_unavailable')
    if item.status not in ('draft','approved') or item.direction!='outbound' or not item.body_ciphertext:blockers.append('draft_unavailable')
    else:
        try:
            text=unseal('message',item.body_ciphertext)
            if not isinstance(text,str) or not text.strip() or len(text.encode())>1000:blockers.append('draft_unavailable')
        except HTTPException:blockers.append('draft_unavailable')
    inbound=db.scalar(select(MetaMessage).where(MetaMessage.conversation_id==conversation.id,MetaMessage.status=='received',MetaMessage.direction=='inbound',MetaMessage.external_id.is_not(None)).order_by(MetaMessage.occurred_at.desc(),MetaMessage.id.desc()).limit(1))
    timestamp=instant(inbound.occurred_at) if inbound else None
    proof=inbox_proves(db,conversation,inbound)
    if not proof:blockers.append('trusted_inbound_missing')
    if not timestamp or timestamp>at:blockers.append('inbound_time_unverified')
    # Age is a fact, not an allowed sending window. Never infer eligibility from 24h.
    age=int((at-timestamp).total_seconds()) if timestamp and timestamp<=at else None
    fields=[item.id,item.body_ciphertext,item.status,item.approved_by,conversation.id,conversation.account_id,conversation.peer_id,
            conversation.opted_out,salon.owner_id if salon else None,salon.status if salon else None,
            inbound.id if inbound else None,inbound.occurred_at if inbound else None,proof,
            credential.checked_at if credential else None,credential.revoked if credential else None,
            [credential.username,credential.subject_id,credential.config_id,credential.expires_at,credential.token_ciphertext] if credential else None]
    fingerprint=hashlib.sha256(json.dumps(fields,separators=(',',':')).encode()).hexdigest()
    if payload.expected_fingerprint and payload.expected_fingerprint!=fingerprint:blockers.append('review_stale')
    return {'can_send':False,'transport_implemented':False,'contract_status':'blocked','owner_api_approval':False,
            'blocking_reasons':list(dict.fromkeys(blockers)),'inbound_provenance':'processed_webhook' if proof else 'unverified',
            'inbound_age_seconds':age,'window_policy_verified':False,'review_fingerprint':fingerprint,
            'note':'To podgląd lokalny, nie zgoda ani rezerwacja wysyłki. Nie zmieniono statusu wiadomości.'}
