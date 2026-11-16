from decimal import Decimal
from scripts.codex_automation.queue_policy import Gate, decide


def gate(**changes):
    values = dict(
        billing_month="2026-11", current_month="2026-11",
        spend_usd=Decimal("0.03"), pending_reservations_usd=Decimal("0"),
        provider_hard_cap_verified=True, key_scoped_to_project=True,
        approved_issues=frozenset({28, 29, 30, 31}),
        passed_issues=frozenset(), running_issues=frozenset(),
    )
    values.update(changes)
    return Gate(**values)


def test_next_issue():
    assert decide(gate()) == ("READY", 28)
    assert decide(gate(passed_issues=frozenset({28}))) == ("READY", 29)


def test_fail_closed_without_billing_or_cap():
    assert decide(gate(spend_usd=None))[0] == "BLOCKED_SPEND_UNKNOWN"
    assert decide(gate(provider_hard_cap_verified=False))[0] == "BLOCKED_PROJECT_CAP_OR_KEY"
    assert decide(gate(billing_month="2026-10"))[0] == "BLOCKED_STALE_BILLING"


def test_budget_includes_pending_and_reservation():
    assert decide(gate(spend_usd=Decimal("6.01")))[0] == "BLOCKED_MONTHLY_BUDGET"
    assert decide(gate(pending_reservations_usd=Decimal("6")))[0] == "BLOCKED_MONTHLY_BUDGET"


def test_single_runner_and_approval():
    assert decide(gate(running_issues=frozenset({28})))[0] == "WAIT_ACTIVE_RUN"
    assert decide(gate(approved_issues=frozenset())) == ("WAIT_EXPLICIT_APPROVAL", 28)
