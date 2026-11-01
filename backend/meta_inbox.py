"""Durable encrypted inbox: signature -> commit -> HTTP ack; no provider I/O here."""
import hashlib,json,logging,os,time,uuid
from datetime import datetime,timedelta,timezone
from sqlalchemy import select,update,delete,func,or_,and_,text
from sqlalchemy.exc import IntegrityError
from backend.db import Session,Salon,now
from backend.meta_models import MetaWebhookInbox,MetaConversation,MetaMessage,MetaCredential

MAX_BODY=65536
MAX_EVENTS=50
BATCH=4
LEASE_SECONDS=120
MAX_ATTEMPTS=5
log=logging.getLogger('meta.inbox')
_last_alert=0.0

def insert_for(db,model):
    if db.bind.dialect.name=='postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert(model)

def persist(payload):
    """Separate bounded transaction. Never locks a credential or processes CRM."""
    from backend.meta import seal
    rows=[]
    for entry in payload['entry']:
        if not isinstance(entry,dict) or str(entry.get('id',''))!=os.environ['META_TEST_ACCOUNT_ID']:continue
        events=entry.get('messaging',[])
        if not isinstance(events,list):continue
        for event in events:
            if not isinstance(event,dict):continue
            if len(rows)>=MAX_EVENTS:raise ValueError('Event limit')
            message=event.get('message',{})
            if not isinstance(message,dict):continue
            mid=message.get('mid')
            # Include event kind so deletion/echo never collide with an inbound mid.
            kind='deleted' if message.get('is_deleted') else 'echo' if message.get('is_echo') else 'message'
            identity=[entry['id'],kind,mid] if isinstance(mid,str) and mid else event
            key=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            stored_event=event
            if message.get('is_deleted'):
                # Nie przechowujemy ewentualnego tekstu/załączników w tombstone.
                stored_event={'sender':{'id':peer_id(event,'sender')},'recipient':{'id':peer_id(event,'recipient')},'timestamp':event.get('timestamp'),'message':{'mid':mid,'is_deleted':True,'is_echo':message.get('is_echo') is True}}
            wrapped={'object':'instagram','entry':[{'id':entry['id'],'messaging':[stored_event]}]}
            rows.append(dict(id=str(uuid.uuid4()),dedup_key=key,account_id=str(entry['id']),payload_ciphertext=seal('inbox',wrapped),status='pending',attempts=0,next_attempt_at='',lease_until='',lease_token='',created_at=now(),updated_at=now(),processed_at='',last_error='',dead_letter=0))
    with Session() as db:
        if db.bind.dialect.name=='postgresql':
            db.execute(text("SET LOCAL lock_timeout='500ms'"))
            db.execute(text("SET LOCAL statement_timeout='2000ms'"))
        if rows:
            db.execute(insert_for(db,MetaWebhookInbox).values(rows).on_conflict_do_nothing(index_elements=['dedup_key']))
        db.commit()
    return len(rows)

def scrub_message_payloads(db,account,mid):
    """Usunięcie wiadomości obejmuje również trwałe kopie jej tekstu w inboxie."""
    accounts=[str(account)]
    # Zgodność z 3.0.3, która zachowywała typ liczbowego entry.id w kluczu.
    if str(account).isdecimal():accounts.append(int(account))
    keys=[hashlib.sha256(json.dumps([a,kind,mid],sort_keys=True,separators=(',',':')).encode()).hexdigest() for a in accounts for kind in ('message','echo','deleted')]
    db.execute(update(MetaWebhookInbox).where(MetaWebhookInbox.account_id==str(account),MetaWebhookInbox.dedup_key.in_(keys)).values(payload_ciphertext='',status='done',processed_at=now(),updated_at=now(),lease_token='',lease_until='',last_error='',dead_letter=0))

def peer_id(event,key):
    identity=event.get(key)
    if not isinstance(identity,dict):return ''
    value=identity.get('id','')
    return str(value) if isinstance(value,(str,int)) and not isinstance(value,bool) else ''

def apply_payload(db,payload):
    from backend.meta import seal,opt_out,audit,uid
    for entry in payload['entry']:
        if not isinstance(entry,dict) or str(entry.get('id',''))!=os.environ['META_TEST_ACCOUNT_ID']:continue
        grant=db.scalar(select(MetaCredential).where(MetaCredential.account_id==os.environ['META_TEST_ACCOUNT_ID']).with_for_update())
        if grant and grant.revoked:continue
        events=entry.get('messaging',[])
        if not isinstance(events,list):continue
        for event in events:
            if not isinstance(event,dict):continue
            message=event.get('message',{})
            if not isinstance(message,dict):continue
            mid=message.get('mid')
            if not isinstance(mid,str) or not 0<len(mid)<=250:continue
            sender=peer_id(event,'sender');recipient=peer_id(event,'recipient')
            account=os.environ['META_TEST_ACCOUNT_ID'];echo=sender==account and message.get('is_echo') is True
            if not echo and recipient!=account:continue
            peer=recipient if echo else sender
            if not peer or peer==account or len(peer)>100:continue
            try:at=datetime.fromtimestamp(int(event['timestamp'])/1000,timezone.utc)
            except (KeyError,ValueError,TypeError,OverflowError,OSError):continue
            if at>datetime.now(timezone.utc)+timedelta(minutes=5) or at<datetime.now(timezone.utc)-timedelta(days=90):continue
            c=db.scalar(select(MetaConversation).where(MetaConversation.account_id==account,MetaConversation.peer_id==peer).with_for_update())
            if not c:
                try:
                    with db.begin_nested():
                        c=MetaConversation(id=uid(),account_id=account,peer_id=peer);db.add(c);db.flush()
                except IntegrityError:c=db.scalar(select(MetaConversation).where(MetaConversation.account_id==account,MetaConversation.peer_id==peer).with_for_update())
            existing=db.scalar(select(MetaMessage).where(MetaMessage.conversation_id==c.id,MetaMessage.external_id==mid))
            if existing:
                if message.get('is_deleted') or existing.status=='deleted':
                    newly_deleted=existing.status!='deleted'
                    existing.body_ciphertext='';existing.status='deleted';scrub_message_payloads(db,account,mid)
                    if newly_deleted and c.salon_id:
                        salon=db.get(Salon,c.salon_id)
                        audit(db,c,salon.owner_id,'instagram_deleted','Webhook Meta potwierdził usunięcie; źródło meta_message:'+existing.id)
                continue
            deleted=bool(message.get('is_deleted'));text=message.get('text','')
            if deleted:scrub_message_payloads(db,account,mid)
            if not isinstance(text,str):text=''
            text=text[:10000]
            item=MetaMessage(id=uid(),conversation_id=c.id,external_id=mid,status='deleted' if deleted else 'api_confirmed_sent' if echo else 'received',direction='outbound' if echo else 'inbound',body_ciphertext=seal('message',text) if text and not deleted and at>datetime.now(timezone.utc)-timedelta(days=30) else '',occurred_at=at.isoformat())
            try:
                with db.begin_nested():db.add(item);db.flush()
            except IntegrityError:continue
            if not echo and not deleted:
                c.last_inbound_at=max(c.last_inbound_at or '',at.isoformat())
                if opt_out(text):c.opted_out=1
            if c.salon_id:
                salon=db.get(Salon,c.salon_id)
                audit(db,c,salon.owner_id,'instagram_deleted' if deleted else 'instagram_received' if not echo else 'instagram_sent','Webhook Meta potwierdził zdarzenie; źródło meta_message:'+item.id)

def claim_batch(at=None):
    at=at or datetime.now(timezone.utc)
    stamp=at.isoformat()
    with Session() as db:
        eligible=or_(and_(MetaWebhookInbox.status.in_(('pending','failed')),MetaWebhookInbox.next_attempt_at<=stamp),and_(MetaWebhookInbox.status=='processing',MetaWebhookInbox.lease_until<stamp))
        rows=list(db.scalars(select(MetaWebhookInbox).where(eligible,MetaWebhookInbox.dead_letter==0).order_by(MetaWebhookInbox.created_at,MetaWebhookInbox.id).with_for_update(skip_locked=True).limit(BATCH)))
        claims=[]
        for row in rows:
            if row.attempts>=MAX_ATTEMPTS:
                row.status='failed';row.dead_letter=1;row.last_error='attempts_exhausted';continue
            row.status='processing';row.attempts+=1;row.lease_token=str(uuid.uuid4());row.lease_until=(at+timedelta(seconds=LEASE_SECONDS)).isoformat();row.updated_at=stamp
            claims.append((row.id,row.lease_token))
        db.commit()
        return claims

def process_claim(id,lease,at=None):
    from backend.meta import unseal
    at=at or datetime.now(timezone.utc)
    try:
        with Session() as db:
            if db.bind.dialect.name=='postgresql':
                db.execute(text("SET LOCAL lock_timeout='500ms'"))
                db.execute(text("SET LOCAL statement_timeout='2000ms'"))
            # Wspólna kolejność blokad z callbackiem prywatności: credential -> inbox.
            # Podgląd nie blokuje wiersza; po blokadzie ponownie sprawdzamy dzierżawę.
            account=db.scalar(select(MetaWebhookInbox.account_id).where(MetaWebhookInbox.id==id))
            if account:
                db.scalar(select(MetaCredential).where(MetaCredential.account_id==account).with_for_update())
            row=db.scalar(select(MetaWebhookInbox).where(MetaWebhookInbox.id==id,MetaWebhookInbox.status=='processing',MetaWebhookInbox.lease_token==lease,MetaWebhookInbox.lease_until>=at.isoformat()).with_for_update())
            if not row:return False
            apply_payload(db,unseal('inbox',row.payload_ciphertext))
            row.status='done';row.processed_at=at.isoformat();row.updated_at=at.isoformat();row.lease_until='';row.last_error=''
            # CRM writes and done status commit atomically; replay cannot duplicate them.
            db.commit()
            return True
    except Exception:
        # Never record exception strings, payloads, identifiers or provider URLs.
        with Session() as db:
            if db.bind.dialect.name=='postgresql':
                db.execute(text("SET LOCAL lock_timeout='500ms'"))
                db.execute(text("SET LOCAL statement_timeout='2000ms'"))
            row=db.scalar(select(MetaWebhookInbox).where(MetaWebhookInbox.id==id,MetaWebhookInbox.status=='processing',MetaWebhookInbox.lease_token==lease).with_for_update())
            if row:
                row.status='failed';row.dead_letter=int(row.attempts>=MAX_ATTEMPTS);row.last_error='processing_failed'
                row.next_attempt_at=(at+timedelta(seconds=min(300,5*2**(row.attempts-1)))).isoformat();row.lease_until='';row.updated_at=at.isoformat();db.commit()
        return False

def drain_once():
    from backend.meta_flags import feature
    # Reception and CRM processing can be paused independently, retaining inbox.
    if not feature('crm_history'):return 0
    claims=claim_batch()
    for id,lease in claims:process_claim(id,lease)
    return len(claims)

def diagnostics(db,at=None):
    at=at or datetime.now(timezone.utc)
    result={}
    for status in ('pending','processing','done','failed'):
        count,oldest=db.execute(select(func.count(),func.min(MetaWebhookInbox.created_at)).where(MetaWebhookInbox.status==status)).one()
        result[status]={'count':count,'oldest_age_seconds':max(0,int((at-datetime.fromisoformat(oldest)).total_seconds())) if oldest else 0}
    result['dead_letter']=db.scalar(select(func.count()).select_from(MetaWebhookInbox).where(MetaWebhookInbox.dead_letter==1))
    result['warning']=result['pending']['count']>=100 or result['pending']['oldest_age_seconds']>300 or result['dead_letter']>0
    return result

def maintenance(db,at=None):
    global _last_alert
    at=at or datetime.now(timezone.utc)
    db.execute(update(MetaWebhookInbox).where(MetaWebhookInbox.status=='done',MetaWebhookInbox.payload_ciphertext!='',MetaWebhookInbox.processed_at<(at-timedelta(days=7)).isoformat()).values(payload_ciphertext=''))
    db.execute(delete(MetaWebhookInbox).where(MetaWebhookInbox.status=='done',MetaWebhookInbox.processed_at<(at-timedelta(days=90)).isoformat()))
    db.commit()
    status=diagnostics(db,at)
    if status['warning'] and time.monotonic()-_last_alert>=60:
        log.warning('Inbox requires owner review: pending=%d oldest_pending_seconds=%d failed=%d dead_letter=%d',status['pending']['count'],status['pending']['oldest_age_seconds'],status['failed']['count'],status['dead_letter'])
        _last_alert=time.monotonic()
    return status
