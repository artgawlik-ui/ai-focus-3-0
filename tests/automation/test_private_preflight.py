"""Offline entrypoint tests. No real DB, OpenAI API or idle loop is invoked."""
from contextlib import redirect_stderr
import importlib.util
from io import StringIO
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/codex_automation/render_private_preflight.py"
spec = importlib.util.spec_from_file_location("private_preflight_under_test", SCRIPT)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PrivatePreflightTests(unittest.TestCase):
    def modules(self, diagnose, idle):
        return {"private_budget_gate_diagnostic": SimpleNamespace(main=diagnose),
                "render_private_bootstrap": SimpleNamespace(main=idle)}

    def test_no_opt_in_or_unknown_option_cannot_execute_anything(self):
        diagnose, idle = Mock(), Mock()
        for args in ([], ["--unknown"], ["--run-diagnostic-and-idle", "--unknown"]):
            with self.subTest(args=args), patch.dict(sys.modules, self.modules(diagnose, idle)), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    preflight.main(args)
                self.assertEqual(raised.exception.code, 2)
        diagnose.assert_not_called()
        idle.assert_not_called()

    def test_successful_diagnostic_precedes_idle(self):
        calls = []
        diagnose = Mock(side_effect=lambda: calls.append("diagnostic"))
        idle = Mock(side_effect=lambda: calls.append("idle"))
        with patch.dict(sys.modules, self.modules(diagnose, idle)):
            preflight.main(["--run-diagnostic-and-idle"])
        self.assertEqual(calls, ["diagnostic", "idle"])
        diagnose.assert_called_once_with()
        idle.assert_called_once_with()

    def test_diagnostic_failure_or_interrupt_never_enters_idle(self):
        for error in (SystemExit("BLOCKED_PRIVATE_DIAGNOSTIC_FAILED"), RuntimeError("synthetic"), KeyboardInterrupt()):
            diagnose, idle = Mock(side_effect=error), Mock()
            with self.subTest(error=type(error).__name__), patch.dict(sys.modules, self.modules(diagnose, idle)):
                with self.assertRaises(type(error)):
                    preflight.main(["--run-diagnostic-and-idle"])
            idle.assert_not_called()

    def test_idle_failure_is_not_retried(self):
        diagnose = Mock()
        idle = Mock(side_effect=SystemExit("BLOCKED_DB_CONNECT_OR_SCHEMA"))
        with patch.dict(sys.modules, self.modules(diagnose, idle)):
            with self.assertRaises(SystemExit):
                preflight.main(["--run-diagnostic-and-idle"])
        diagnose.assert_called_once_with()
        idle.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
