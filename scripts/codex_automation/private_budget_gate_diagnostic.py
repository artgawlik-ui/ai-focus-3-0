"""One-shot, zero-API-cost Render private DB gate diagnostic.

Run only in existing worker network with CODEX_BUDGET_DATABASE_URL.
Uses a PostgreSQL temporary table and rolls back all test changes.
Never prints secrets, URLs, or personally identifying information.
"""
import os
import sys
from decimal import Decimal

from durable_reservations import CAP, RESERVE, BudgetBlocked, reserve_transaction
from render_private_bootstrap import EXPECTED_DB, validate_private_url


class RollbackConnection:
    """Keep reserve_transaction's 'with conn' from committing test changes."""
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.conn.cursor()


def main():
    url = os.environ.get("CODEX_BUDGET_DATABASE_URL", "")
    if validate_private_url(url):
        raise SystemExit("BLOCKED_PRIVATE_DB_VALIDATION")
    try:
        import psycopg
    except ImportError:
        raise SystemExit("BLOCKED_PSYCOPG_REQUIRED")
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database()")
                if cur.fetchone()[0] != EXPECTED_DB:
                    raise RuntimeError("WRONG_DATABASE")
                # Session-local shadow of the real table. Nothing touches persistent rows.
                cur.execute("CREATE TEMP TABLE codex_budget_reservations (LIKE public.codex_budget_reservations INCLUDING ALL) ON COMMIT DROP")
            wrapped = RollbackConnection(conn)
            reserve_transaction(wrapped, month="diagnostic-only", issue=900001,
                                provider_spend=Decimal("0"), reservation_id="diag-1",
                                provider_verified=True)
            print("PASS: reservation accepted", flush=True)
            for label, kwargs in [
                ("budget exceeded", dict(month="diagnostic-only", issue=900002,
                                         provider_spend=CAP, reservation_id="diag-2",
                                         provider_verified=True)),
                ("unverified spend", dict(month="diagnostic-only", issue=900003,
                                          provider_spend=Decimal("0"), reservation_id="diag-3",
                                          provider_verified=False)),
            ]:
                try:
                    reserve_transaction(wrapped, **kwargs)
                except BudgetBlocked:
                    print("PASS: " + label + " blocked", flush=True)
                else:
                    raise RuntimeError("GATE_FAILED_" + label.replace(" ", "_"))
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM codex_budget_reservations")
                if cur.fetchone()[0] != 1:
                    raise RuntimeError("UNEXPECTED_RESERVATION_COUNT")
            conn.rollback()
            print("PASS: diagnostic transaction rolled back; no paid API calls", flush=True)
            print("UNKNOWN: cross-connection concurrency requires separate controlled test", flush=True)
    except Exception:
        raise SystemExit("BLOCKED_PRIVATE_DIAGNOSTIC_FAILED") from None


if __name__ == "__main__":
    main()
