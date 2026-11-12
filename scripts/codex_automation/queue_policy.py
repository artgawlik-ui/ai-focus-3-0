"""Fail-closed queue admission policy; no API calls or paid execution.

A trusted scheduler may call decide() with independently verified billing data.
Never source spend or approvals from issue text, PRs, or untrusted artifacts.
"""
from dataclasses import dataclass
from decimal import Decimal

MONTHLY_CAP = Decimal("8.00")
# Conservative reservation, not a prediction or a replacement for provider hard cap.
PER_TASK_RESERVE = Decimal("2.00")
ORDER = (28, 29, 30, 31)


@dataclass(frozen=True)
class Gate:
    billing_month: str
    current_month: str
    spend_usd: Decimal | None
    pending_reservations_usd: Decimal | None
    provider_hard_cap_verified: bool
    key_scoped_to_project: bool
    approved_issues: frozenset[int]
    passed_issues: frozenset[int]
    running_issues: frozenset[int]


def decide(gate: Gate) -> tuple[str, int | None]:
    """Return (reason, issue); only READY allows an orchestrator to proceed."""
    if gate.billing_month != gate.current_month:
        return "BLOCKED_STALE_BILLING", None
    if not gate.provider_hard_cap_verified or not gate.key_scoped_to_project:
        return "BLOCKED_PROJECT_CAP_OR_KEY", None
    if gate.spend_usd is None or gate.pending_reservations_usd is None:
        return "BLOCKED_SPEND_UNKNOWN", None
    if gate.spend_usd < 0 or gate.pending_reservations_usd < 0:
        return "BLOCKED_INVALID_SPEND", None
    if gate.spend_usd + gate.pending_reservations_usd + PER_TASK_RESERVE > MONTHLY_CAP:
        return "BLOCKED_MONTHLY_BUDGET", None
    if gate.running_issues:
        return "WAIT_ACTIVE_RUN", None
    for issue in ORDER:
        if issue in gate.passed_issues:
            continue
        if issue not in gate.approved_issues:
            return "WAIT_EXPLICIT_APPROVAL", issue
        return "READY", issue
    return "QUEUE_COMPLETE", None
