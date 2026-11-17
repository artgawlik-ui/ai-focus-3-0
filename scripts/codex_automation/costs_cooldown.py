"""Preserve an operator-established provider cooldown across worker restarts."""
from datetime import datetime, timezone
import re

def wait_for_costs_window(env, stop, logger, *, clock=lambda: datetime.now(timezone.utc)):
    value = env.get('FOCUS_COSTS_NOT_BEFORE_UTC')
    if value is None:
        return not stop.is_set()
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise ValueError('INVALID_COSTS_NOT_BEFORE')
    deadline = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    announced = False
    while not stop.is_set():
        remaining = (deadline - clock()).total_seconds()
        if remaining <= 0:
            return True
        if not announced:
            logger('WAIT: COSTS_COOLDOWN_PRESERVED')
            announced = True
        stop.wait(min(remaining, 60))
    return False
