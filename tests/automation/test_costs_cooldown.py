import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from pathlib import Path
from scripts.codex_automation.costs_cooldown import wait_for_costs_window

NOW=datetime(2026,11,17,16,tzinfo=timezone.utc)
class CooldownTests(unittest.TestCase):
    def test_deadline_survives_restart(self):
        for _ in range(2):
            stop=Mock(); stop.is_set.side_effect=[False,True]
            logs=[]
            self.assertFalse(wait_for_costs_window(
                {'FOCUS_COSTS_NOT_BEFORE_UTC':'2026-11-18T15:37:38Z'},
                stop,logs.append,clock=lambda:NOW))
            stop.wait.assert_called_once_with(60)
            self.assertEqual(logs,['WAIT: COSTS_COOLDOWN_PRESERVED'])

    def test_not_ready_until_deadline(self):
        stop=Mock(); stop.is_set.return_value=False
        clock=Mock(side_effect=[NOW,NOW+timedelta(seconds=60)])
        self.assertTrue(wait_for_costs_window(
            {'FOCUS_COSTS_NOT_BEFORE_UTC':'2026-11-17T16:01:00Z'},
            stop,lambda s:None,clock=clock))
        stop.wait.assert_called_once_with(60)

    def test_invalid_configuration_fails_closed(self):
        for value in ('','garbage','2026-11-18T15:37:38','2026-99-18T15:37:38Z'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                wait_for_costs_window({'FOCUS_COSTS_NOT_BEFORE_UTC':value},Mock(),Mock())

    def test_shutdown_and_unconfigured(self):
        stop=Mock();stop.is_set.return_value=True
        self.assertFalse(wait_for_costs_window({},stop,Mock()))
        stop.is_set.return_value=False
        self.assertTrue(wait_for_costs_window({},stop,Mock()))
        stop.wait.assert_not_called()

    def test_production_order_places_diagnostic_before_cooldown_before_serve(self):
        source=(Path(__file__).resolve().parents[2]/'scripts/codex_automation/github_budget_transport.py').read_text()
        main=source.split('def main(')[1]
        self.assertLess(main.index('emit_snapshot(diagnostic_conn'),main.index('if wait_for_costs_window'))
        self.assertLess(main.index('if wait_for_costs_window'),main.index('serve(api, connect'))
