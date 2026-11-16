"""Offline validation tests: no secrets, network or database."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "codex_automation"))
from render_private_bootstrap import validate_private_url, EXPECTED_HOST, EXPECTED_DB

def test_private_url():
    good = f"postgresql://user:dummy@{EXPECTED_HOST}:5432/{EXPECTED_DB}"
    assert validate_private_url(good) == ""
    assert validate_private_url("") == "BLOCKED_DB_URL_MISSING"
    assert validate_private_url("bad") == "BLOCKED_DB_URL_SCHEME"
    assert validate_private_url(f"postgresql://user:dummy@evil.example/{EXPECTED_DB}") == "BLOCKED_DB_URL_HOST"
    assert validate_private_url(f"postgresql://user:dummy@{EXPECTED_HOST}/other") == "BLOCKED_DB_URL_NAME"
    assert validate_private_url(f"postgresql://user@{EXPECTED_HOST}/{EXPECTED_DB}") == "BLOCKED_DB_URL_AUTH"
