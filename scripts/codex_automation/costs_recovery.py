"""Explicit startup cost observation; never starts a model or changes the database."""
from datetime import datetime, timedelta, timezone
import json

try:
    from .live_cost_gate import CostGateBlocked, check_live_costs
except ImportError:
    from live_cost_gate import CostGateBlocked, check_live_costs


def observe_recovery(env, stop, logger, *, reader=None,
                     clock=lambda: datetime.now(timezone.utc)):
    if env.get('FOCUS_COSTS_RECOVERY_PROBE') != 'true' or stop.is_set():
        return not stop.is_set()
    now = clock()
    try:
        observation = check_live_costs(env=env, now=now, reader=reader)
    except CostGateBlocked as exc:
        limited = str(exc) == 'COSTS_RATE_LIMITED'
        delay = getattr(exc, 'retry_after_seconds', None) if limited else 900
        if type(delay) is not int or not 900 <= delay <= 86400:
            delay = 900
        logger('COSTS_RECOVERY_DIAGNOSTIC: ' + json.dumps({
            'status': 'BLOCKED',
            'code': 'COSTS_RATE_LIMITED' if limited else 'COSTS_UNAVAILABLE',
            'retry_after_seconds': delay,
            'not_before_utc': (clock()+timedelta(seconds=delay)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }, sort_keys=True))
        # Preserve actual provider backoff before the regular controller can
        # admit anything. No probe retry; normal admission still rechecks Costs.
        stop.wait(delay)
        return not stop.is_set()
    logger('COSTS_RECOVERY_DIAGNOSTIC: ' + json.dumps({
        'status': 'PASS', 'observed_at': now.isoformat(),
        'billing_month': observation.billing_month,
        'provider_spend_usd': str(observation.spend_usd),
        'covered_until': observation.covered_until.isoformat(),
    }, sort_keys=True))
    return not stop.is_set()
