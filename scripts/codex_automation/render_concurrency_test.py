"""Integration test for PostgreSQL concurrent reservations, run only in isolated Render.

Needs CODEX_BUDGET_DATABASE_URL (private .internal), psycopg installed.
Uses a test month and unique issue IDs; does not invoke paid APIs.
"""
import os
import threading
import uuid
from decimal import Decimal

from render_private_bootstrap import private_url
from durable_reservations import reserve_transaction, BudgetBlocked

def main():
    url = os.environ.get("CODEX_BUDGET_DATABASE_URL", "")
    if not private_url(url):
        raise SystemExit("BLOCKED_PRIVATE_DB_URL_REQUIRED")
    import psycopg
    month = "test-" + uuid.uuid4().hex[:12]
    barrier = threading.Barrier(2)
    outcomes = []
    lock = threading.Lock()

    def attempt(issue):
        try:
            with psycopg.connect(url, connect_timeout=10) as conn:
                barrier.wait(timeout=15)
                reserve_transaction(conn, month=month, issue=issue,
                                    provider_spend=Decimal("0.10"),
                                    reservation_id=uuid.uuid4().hex,
                                    provider_verified=True)
            result = "RESERVED"
        except BudgetBlocked:
            result = "BLOCKED"
        except Exception as exc:
            result = type(exc).__name__
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt, args=(n,)) for n in (990001, 990002)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=25)
    if sorted(outcomes) != ["BLOCKED", "RESERVED"]:
        raise SystemExit("FAIL_CONCURRENCY: " + repr(outcomes))
    print("PASS: one reservation, one blocked; no paid calls")

if __name__ == "__main__":
    main()
