"""No paid API, no database; adapter integration contract tests."""
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
import json

from scripts.codex_automation.openai_costs import CostsUnavailable, read_project_costs
from scripts.codex_automation.durable_reservations import (
    BudgetBlocked, reserve_transaction,
)


class Response(BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


def fake_open(request, timeout):
    return Response(json.dumps({"data": [{
        "end_time": 1794441600,
        "results": [{"project_id": "proj_test", "amount": {
            "currency": "usd", "value": 0.15}}]}]}).encode())


def test_read_only_costs():
    now = datetime.fromtimestamp(1794445200, timezone.utc)
    amount, _ = read_project_costs(
        admin_key="dummy", project_id="proj_test",
        month_start=1793491200, now=now, opener=fake_open)
    assert amount == Decimal("0.15")


def test_missing_key_blocks():
    try:
        read_project_costs(admin_key="", project_id="proj_test",
                           month_start=0, now=datetime.now(timezone.utc),
                           opener=fake_open)
    except CostsUnavailable:
        return
    assert False, "expected failure"


class FakeCursor:
    def __init__(self, pending):
        self.pending = pending
        self.sql = []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def execute(self, query, params):
        self.sql.append((query, params))
    def fetchone(self):
        return (self.pending,)


class FakeConn:
    def __init__(self, pending=0):
        self.cur = FakeCursor(pending)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def cursor(self):
        return self.cur


def test_budget_and_atomic_reservation_contract():
    conn = FakeConn()
    reserve_transaction(conn, month="2026-11", issue=28,
                        provider_spend=Decimal("0.10"),
                        reservation_id="test-28", provider_verified=True)
    assert "pg_advisory_xact_lock" in conn.cur.sql[0][0]
    assert "INSERT" in conn.cur.sql[-1][0]


def test_over_budget_blocks_before_insert():
    conn = FakeConn(Decimal("4.00"))
    try:
        reserve_transaction(conn, month="2026-11", issue=28,
                            provider_spend=Decimal("3.00"),
                            reservation_id="test-28", provider_verified=True)
    except BudgetBlocked:
        assert not any("INSERT" in query for query, _ in conn.cur.sql)
        return
    assert False, "expected budget block"


def test_unverified_provider_blocks():
    try:
        reserve_transaction(FakeConn(), month="2026-11", issue=28,
                            provider_spend=Decimal("0"),
                            reservation_id="test-28", provider_verified=False)
    except BudgetBlocked:
        return
    assert False, "expected provider block"
