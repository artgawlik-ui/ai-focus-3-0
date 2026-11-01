"""Explicit module overrides opt into the 3.0.3 config migration; legacy unchanged."""
import os
from fastapi import HTTPException

MODULES=('oauth','webhook_verify','ingest','crm_history','diagnostics')

def legacy_enabled():
    return os.getenv('META_ENABLED','false').lower()=='true'

def feature(name):
    if name not in MODULES:raise ValueError('Unknown Meta module')
    value=os.getenv('META_'+name.upper()+'_ENABLED')
    return legacy_enabled() if value is None else value.lower()=='true'

def dm_enabled():
    # No inheritance: empty, missing or unparseable must fail closed.
    return os.getenv('META_DM_TRANSPORT_ENABLED','false').lower()=='true'

def send_dm(*args,**kwargs):
    """The guard belongs INSIDE the boundary, including direct internal calls.

    This release deliberately has no HTTP sending implementation, even when the
    switch is set. Approvals/manual status never invoke a provider transport.
    """
    if not dm_enabled():raise HTTPException(403,'Transport Instagram DM wyłączony')
    raise HTTPException(501,'Transport Instagram DM nie został uruchomiony')
