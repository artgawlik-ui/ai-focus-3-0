"""Postgres reservation transaction: inject an authenticated DB-API connection.

This module NEVER creates a database, connects to production, or stores secrets.
Provision the schema in a dedicated non-production DB after explicit approval.
"""
from decimal import Decimal

CAP = Decimal("8.00")
RESERVE = Decimal("2.00")
SCHEMA = """
CREATE TABLE IF NOT EXISTS codex_budget_reservations (
    reservation_id text PRIMARY KEY,
    month text NOT NULL,
    issue_number integer NOT NULL,
    amount_usd numeric(10,4) NOT NULL CHECK (amount_usd > 0),
    state text NOT NULL CHECK (state IN ('reserved','settled','blocked')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (month, issue_number)
);
CREATE UNIQUE INDEX IF NOT EXISTS codex_one_active_month
ON codex_budget_reservations(month) WHERE state = 'reserved';
"""


class BudgetBlocked(RuntimeError):
    pass


def reserve_transaction(conn, *, month: str, issue: int, provider_spend: Decimal,
                        reservation_id: str, provider_verified: bool) -> None:
    """One transaction, serialized by a PostgreSQL advisory lock.

    Caller must use a durable shared DB and ensure no other path bypasses gate.
    """
    if not provider_verified or not month or issue < 1 or not reservation_id:
        raise BudgetBlocked("PROVIDER_OR_APPROVAL_MISSING")
    if not provider_spend.is_finite() or provider_spend < 0:
        raise BudgetBlocked("INVALID_SPEND")
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("focus-codex-" + month,))
                cur.execute(
                    "SELECT COALESCE(SUM(amount_usd),0) FROM codex_budget_reservations "
                    "WHERE month=%s AND state='reserved'", (month,))
                reserved = Decimal(str(cur.fetchone()[0]))
                if provider_spend + reserved + RESERVE > CAP:
                    raise BudgetBlocked("MONTHLY_BUDGET")
                cur.execute(
                    "INSERT INTO codex_budget_reservations "
                    "(reservation_id,month,issue_number,amount_usd,state) "
                    "VALUES (%s,%s,%s,%s,'reserved')",
                    (reservation_id, month, issue, RESERVE))
    except BudgetBlocked:
        raise
    except Exception:
        raise BudgetBlocked("RESERVATION_UNAVAILABLE") from None
