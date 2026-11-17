"""Bind production gateway startup to the exact private receipt; no model calls."""
import re
from decimal import Decimal
try:
    from . import github_budget_transport as transport
except ImportError:
    import github_budget_transport as transport

def require_private_admission(env, payload, policy, state_dir, api):
    task = transport.validate(payload)
    if (env.get('GITHUB_REPOSITORY') != transport.policy.REPO
            or env.get('GITHUB_REF') != 'refs/heads/main'
            or env.get('GITHUB_RUN_ATTEMPT') != '1'
            or env.get('GITHUB_RUN_ID') != str(payload['run_id'])
            or env.get('GITHUB_SHA') != task.base
            or env.get('APPROVED_BASE') != task.base
            or env.get('APPROVED_NUMBER') != str(task.issue)
            or env.get('APPROVED_DIGEST') != task.digest
            or env.get('APPROVED_BRANCH') != 'codex/issue-'+str(task.issue)
            or state_dir != '/run/focus-codex-'+str(payload['run_id'])+'-1'
            or env.get('MODEL') != policy.model):
        raise transport.TransportBlocked('GATEWAY_ADMISSION_CONTEXT_MISMATCH')
    # Existing controller always commits exactly2USD. Never grant a larger local quota.
    if type(policy.budget) is not int or not 0 < policy.budget <= 2_000_000_000:
        raise transport.TransportBlocked('GATEWAY_ALLOWANCE_MISMATCH')
    # Authenticated GitHub statuses: exact nonce context/run/attempt/SHA and creator.
    # This checks the already committed receipt; it never invokes Costs or reserves.
    transport.wait_receipt(api, payload, timeout=1)
