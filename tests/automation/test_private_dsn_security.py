"""Synthetic, offline tests: never connect to a database or print a DSN."""
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "codex_automation"
sys.path.insert(0, str(SCRIPT_DIR))
spec = importlib.util.spec_from_file_location("private_dsn_under_test", SCRIPT_DIR / "render_private_bootstrap.py")
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class PrivateDsnSecurityTests(unittest.TestCase):
    def setUp(self):
        self.uri = f"postgresql://synthetic:dummy@{bootstrap.EXPECTED_HOST}:5432/{bootstrap.EXPECTED_DB}"

    def test_canonical_private_uri_remains_valid(self):
        self.assertEqual(bootstrap.validate_private_url(self.uri), "")
        self.assertEqual(bootstrap.validate_private_url(self.uri.replace(":5432/", "/")), "")

    def test_options_and_fragments_block_before_driver(self):
        driver = Mock()
        for suffix in ("?host=example.invalid", "?hostaddr=192.0.2.1", "?dbname=other",
                       "?service=other", "?sslmode=disable", "?", "#fragment", "#"):
            with self.subTest(suffix=suffix), patch.dict(os.environ, {"CODEX_BUDGET_DATABASE_URL": self.uri + suffix}), patch.dict(sys.modules, {"psycopg": driver}):
                with self.assertRaises(SystemExit) as raised:
                    bootstrap.main()
                self.assertEqual(str(raised.exception), "BLOCKED_DB_URL_OPTIONS")
        driver.connect.assert_not_called()

    def test_controls_cannot_be_normalized_away(self):
        for control in ("\n", "\r", "\t", "\x00", "\x7f"):
            with self.subTest(control=repr(control)):
                self.assertEqual(bootstrap.validate_private_url(control + self.uri), "BLOCKED_DB_URL_INVALID")

    def test_database_path_must_be_canonical(self):
        for path in ("//" + bootstrap.EXPECTED_DB, "/%61" + bootstrap.EXPECTED_DB[1:], "/other"):
            with self.subTest(path=path):
                uri = self.uri.rsplit("/", 1)[0] + path
                self.assertEqual(bootstrap.validate_private_url(uri), "BLOCKED_DB_URL_NAME")

    def test_non_string_input_fails_with_safe_code(self):
        self.assertEqual(bootstrap.validate_private_url(123), "BLOCKED_DB_URL_INVALID")


if __name__ == "__main__":
    unittest.main()
