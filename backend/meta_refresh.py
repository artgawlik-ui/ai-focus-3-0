"""Single-flight token validation. Network errors NEVER revoke a stored grant."""
import uuid
from datetime import datetime,timedelta,timezone
import httpx
from fastapi import HTTPException
from sqlalchemy import select,or_
from backend.db import Session,now
from backend.meta_models import MetaCredential,MetaRefreshState
from backend.meta_inbox import insert_for

LEASE=90
MAX_ATTEMPTS=3

def check(account_id,at=None):
    from backend.meta import validate_token,unseal,ConfirmedRevoked
    at=at or datetime.now(timezone.utc)
    stamp=at.isoformat();lease=str(uuid.uuid4())
    with Session() as db:
        row=db.get(MetaCredential,account_id)
        if not row or row.revoked or not row.token_ciphertext:raise HTTPException(409,'Wymagana ponowna autoryzacja')
        ciphertext=row.token_ciphertext
        db.execute(insert_for(db,MetaRefreshState).values(account_id=account_id,lease_until='',lease_token='',status='idle',attempts=0,next_attempt_at='',last_error='').on_conflict_do_nothing(index_elements=['account_id']))
        state=db.scalar(select(MetaRefreshState).where(MetaRefreshState.account_id==account_id).with_for_update())
        if state.lease_until>stamp or state.next_attempt_at>stamp:
            db.rollback();raise HTTPException(409,'Sprawdzanie w toku lub oczekuje na ponowienie')
        attempts=state.attempts+1 if state.status in ('retry','checking') else 1
        if attempts>MAX_ATTEMPTS:
            state.status='failed';state.lease_until='';state.next_attempt_at=(at+timedelta(hours=24)).isoformat();db.commit()
            raise HTTPException(503,'Limit prób sprawdzania; token zachowany')
        state.status='checking';state.attempts=attempts;state.lease_until=(at+timedelta(seconds=LEASE)).isoformat();state.lease_token=lease
        db.commit() # No database locks/connection held while waiting for Meta.
    debug=None;error='';revoked=False
    try:
        with httpx.Client(timeout=10,follow_redirects=False) as client:
            debug=validate_token(client,unseal('token',ciphertext))
    except ConfirmedRevoked:revoked=True
    except Exception:error='validation_failed' # Raw provider exceptions may contain secrets.
    with Session() as db:
        state=db.scalar(select(MetaRefreshState).where(MetaRefreshState.account_id==account_id).with_for_update())
        if not state or state.lease_token!=lease:raise HTTPException(409,'Wynik starszego sprawdzania pominięty')
        row=db.scalar(select(MetaCredential).where(MetaCredential.account_id==account_id).with_for_update())
        if not row or row.revoked or row.token_ciphertext!=ciphertext:
            state.status='idle';state.lease_until='';state.next_attempt_at='';db.commit()
            raise HTTPException(409,'Poświadczenie zmieniło się podczas sprawdzania')
        state.lease_until=''
        if revoked:
            row.revoked=1;row.token_ciphertext='';state.status='revoked';state.last_error='debug_invalid';state.next_attempt_at=''
        elif error:
            state.status='retry' if attempts<MAX_ATTEMPTS else 'failed';state.last_error=error
            delay=5*2**(attempts-1) if attempts<MAX_ATTEMPTS else 86400
            state.next_attempt_at=(at+timedelta(seconds=delay)).isoformat()
        else:
            expiry=int(debug.get('expires_at',0));row.expires_at=datetime.fromtimestamp(expiry,timezone.utc).isoformat() if expiry else '';row.checked_at=stamp
            state.status='valid';state.attempts=0;state.last_error='';state.next_attempt_at=''
        db.commit()
    if revoked:raise HTTPException(502,'debug_token potwierdził unieważnienie; wymagana autoryzacja')
    if error:raise HTTPException(503,'Odświeżenie nieudane, ponów; token zachowany')
    return {'validated':True,'rotated':False,'reauthorize_before_expiry':bool(debug.get('expires_at')),'note':'Unified Login SUAT: kontrola ważności, nie ig_refresh_token; ponowny OAuth przed wygaśnięciem.'}

def maintain():
    from backend.meta_flags import feature
    if not feature('oauth'):return
    cutoff=(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat()
    with Session() as db:
        ids=list(db.scalars(select(MetaCredential.account_id).outerjoin(MetaRefreshState,MetaRefreshState.account_id==MetaCredential.account_id).where(MetaCredential.revoked==0,MetaCredential.token_ciphertext!='',or_(MetaCredential.checked_at<cutoff,MetaRefreshState.status.in_(('retry','checking','failed')))).limit(1)))
    for account in ids:
        try:check(account)
        except HTTPException:pass
