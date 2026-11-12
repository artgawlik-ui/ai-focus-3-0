"""Offline queue transition smoke test. No network, API, secrets, billing, or side effects."""
from decimal import Decimal
from queue_policy import Gate, decide

def gate(**kw):
    defaults = dict(billing_month="2026-11", current_month="2026-11",
                    spend_usd=Decimal("0.03"), pending_reservations_usd=Decimal("0"),
                    provider_hard_cap_verified=True, key_scoped_to_project=True,
                    approved_issues=frozenset({28, 29, 30, 31}),
                    passed_issues=frozenset(), running_issues=frozenset())
    defaults.update(kw)
    return Gate(**defaults)

assert decide(gate()) == ("READY", 28)
assert decide(gate(running_issues=frozenset({28}))) == ("WAIT_ACTIVE_RUN", None)
assert decide(gate(passed_issues=frozenset({28}))) == ("READY", 29)
assert decide(gate(passed_issues=frozenset({28, 29}))) == ("READY", 30)
assert decide(gate(passed_issues=frozenset({28, 29, 30}))) == ("READY", 31)
assert decide(gate(passed_issues=frozenset({28, 29, 30, 31}))) == ("QUEUE_COMPLETE", None)
assert decide(gate(spend_usd=Decimal("6.01")))[0] == "BLOCKED_MONTHLY_BUDGET"
assert decide(gate(spend_usd=None))[0] == "BLOCKED_SPEND_UNKNOWN"
assert decide(gate(provider_hard_cap_verified=False))[0] == "BLOCKED_PROJECT_CAP_OR_KEY"
assert decide(gate(approved_issues=frozenset())) == ("WAIT_EXPLICIT_APPROVAL", 28)
print("PASS: offline queue transitions and fail-closed budget gates")
