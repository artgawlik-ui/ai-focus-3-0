from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
import unittest
from unittest.mock import Mock

from scripts.codex_automation.costs_recovery import observe_recovery
from scripts.codex_automation.openai_costs import CostsUnavailable


class CostsRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 17, 16, 45, tzinfo=timezone.utc)
        self.env = dict(FOCUS_COSTS_RECOVERY_PROBE='true',
                        OPENAI_COSTS_ADMIN_KEY='synthetic-secret',
                        OPENAI_PROJECT_ID='proj_synthetic')
        self.stop = Mock()
        self.stop.is_set.return_value = False
        self.log = Mock()
        self.reader = Mock(return_value=(Decimal('.03'),
            self.now.replace(hour=0, minute=0)))

    def call(self):
        return observe_recovery(self.env, self.stop, self.log,
                                reader=self.reader, clock=lambda: self.now)

    def result(self):
        return json.loads(self.log.call_args.args[0].split(': ', 1)[1])

    def test_opt_in_required_before_any_costs_read(self):
        del self.env['FOCUS_COSTS_RECOVERY_PROBE']
        self.assertTrue(self.call())
        self.reader.assert_not_called()
        self.log.assert_not_called()

    def test_one_live_observation_is_not_inferred_from_ready(self):
        self.assertTrue(self.call())
        self.reader.assert_called_once()
        self.assertEqual(self.result()['status'], 'PASS')
        self.assertEqual(self.result()['provider_spend_usd'], '0.03')
        self.stop.wait.assert_not_called()
        self.assertNotIn('synthetic-secret', str(self.log.call_args))
        self.assertNotIn('proj_synthetic', str(self.log.call_args))

    def test_429_records_and_honors_real_retry_without_probe_retry(self):
        self.reader.side_effect = CostsUnavailable('COSTS_RATE_LIMITED', retry_after_seconds=1800)
        self.assertTrue(self.call())
        self.reader.assert_called_once()
        self.stop.wait.assert_called_once_with(1800)
        self.assertEqual(self.result()['code'], 'COSTS_RATE_LIMITED')
        self.assertEqual(self.result()['not_before_utc'], '2026-11-17T17:15:00Z')

    def test_stop_during_backoff_prevents_polling(self):
        self.reader.side_effect = CostsUnavailable('COSTS_RATE_LIMITED')
        self.stop.wait.side_effect = lambda delay: setattr(self.stop.is_set, 'return_value', True)
        self.assertFalse(self.call())
        self.reader.assert_called_once()
        self.stop.wait.assert_called_once_with(900)

    def test_stale_observation_does_not_report_availability(self):
        self.reader.return_value = (Decimal('.03'), self.now-timedelta(days=2))
        self.assertTrue(self.call())
        self.assertEqual(self.result()['status'], 'BLOCKED')
        self.stop.wait.assert_called_once_with(900)

    def test_stop_before_probe_never_contacts_costs(self):
        self.stop.is_set.return_value = True
        self.assertFalse(self.call())
        self.reader.assert_not_called()
