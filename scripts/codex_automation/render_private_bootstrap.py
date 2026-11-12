"""Private Render DB gate bootstrap. Execute ONLY in isolated trusted Render runner.

Requires DATABASE_URL injected by Render (internal PostgreSQL URL).
Never log URLs, passwords, or OpenAI credentials.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

from durable_reservations import SCHEMA


def private_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return (parsed.scheme in ("postgres", "postgresql")
            and bool(parsed.username) and bool(parsed.password)
            and host.endswith(".internal"))


def main():
    url = os.environ.get("CODEX_BUDGET_DATABASE_URL", "")
    if not private_url(url):
        raise SystemExit("BLOCKED_PRIVATE_DB_URL_REQUIRED")
    try:
        import psycopg
    except ImportError:
        raise SystemExit("BLOCKED_PSYCOPG_REQUIRED")
    with psycopg.connect(url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute("SELECT current_database()")
            assert cur.fetchone()[0] == "ai_focus_codex_budget_gate_test"
    print("PASS: isolated private database schema initialized")


if __name__ == "__main__":
    main()
