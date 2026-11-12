"""Private Render database bootstrap. No URLs or credentials are logged."""
import os
from urllib.parse import unquote, urlsplit

from durable_reservations import SCHEMA

# Exact trusted Render internal DB host, never a user-controlled suffix match.
EXPECTED_HOST = "dpg-dbqp1tuc6qcc7380nd10-a"
EXPECTED_DB = "ai_focus_codex_budget_gate_test"


def validate_private_url(url: str) -> str:
    """Return a non-sensitive error code; never include the URL in errors."""
    if not url:
        return "BLOCKED_DB_URL_MISSING"
    try:
        parsed = urlsplit(url.strip())
        if parsed.scheme not in ("postgres", "postgresql"):
            return "BLOCKED_DB_URL_SCHEME"
        if not parsed.username or not parsed.password:
            return "BLOCKED_DB_URL_AUTH"
        if (parsed.hostname or "").lower() != EXPECTED_HOST:
            return "BLOCKED_DB_URL_HOST"
        if unquote(parsed.path.lstrip("/")) != EXPECTED_DB:
            return "BLOCKED_DB_URL_NAME"
        if parsed.port not in (None, 5432):
            return "BLOCKED_DB_URL_PORT"
    except (ValueError, TypeError):
        return "BLOCKED_DB_URL_INVALID"
    return ""


def main():
    url = os.environ.get("CODEX_BUDGET_DATABASE_URL", "")
    error = validate_private_url(url)
    if error:
        raise SystemExit(error)
    try:
        import psycopg
    except ImportError:
        raise SystemExit("BLOCKED_PSYCOPG_REQUIRED")
    try:
        with psycopg.connect(url.strip(), connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA)
                cur.execute("SELECT current_database()")
                if cur.fetchone()[0] != EXPECTED_DB:
                    raise SystemExit("BLOCKED_WRONG_DATABASE")
    except psycopg.Error:
        raise SystemExit("BLOCKED_DB_CONNECT_OR_SCHEMA") from None
    print("PASS: isolated private database schema initialized")


if __name__ == "__main__":
    main()
