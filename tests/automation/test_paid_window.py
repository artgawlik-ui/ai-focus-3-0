"""Production time gate tests; synthetic counting and generation only."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from scripts.codex_automation.executor_limits import Gateway, Limit, require_paid_window
from tests.automation.test_executor_limits import policy, Fake

def utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()

class PaidWindowTests(unittest.TestCase):
    def test_winter_boundaries(self):
        for value in ('2026-11-16T07:59:59','2026-11-16T17:00:00'):
            with self.subTest(value=value), self.assertRaisesRegex(Limit,'WINDOW_CLOSED'):
                require_paid_window(utc(value))
        for value in ('2026-11-16T08:00:00','2026-11-16T16:59:59'):
            require_paid_window(utc(value))

    def test_summer_timezone(self):
        require_paid_window(utc('2026-07-16T07:00:00'))
        with self.assertRaisesRegex(Limit,'WINDOW_CLOSED'):
            require_paid_window(utc('2026-07-16T16:00:00'))

    def test_outside_window_sends_neither_count_nor_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            fake=Fake()
            # Fixture time is noon; injected guard simulates a closed production window.
            def closed(_): require_paid_window(utc('2026-11-16T17:00:00'))
            gateway=Gateway(policy(),fake,Path(directory)/'ledger',
                wall=lambda:1794830400,admission_guard=closed)
            with self.assertRaisesRegex(Limit,'WINDOW_CLOSED'):
                gateway.exchange(b'{"model":"synthetic-model","input":"test"}')
            self.assertEqual(fake.calls,[])
            self.assertTrue(gateway.stopped)

    def test_closure_during_count_prevents_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            times=iter([utc('2026-11-16T16:59:59'),utc('2026-11-16T17:00:00')])
            fake=Fake()
            gateway=Gateway(policy(),fake,Path(directory)/'ledger',
                wall=lambda:1794830400,admission_guard=lambda _: require_paid_window(next(times)))
            with self.assertRaisesRegex(Limit,'WINDOW_CLOSED'):
                gateway.exchange(b'{"model":"synthetic-model","input":"test"}')
            self.assertEqual([c[0] for c in fake.calls],['input_tokens'])
            self.assertTrue(gateway.stopped)

    def test_production_entrypoint_always_installs_guard(self):
        source=(Path(__file__).resolve().parents[2]/'scripts/codex_automation/executor_limits.py').read_text()
        main=source.split('def main():')[1]
        self.assertLess(main.index('require_paid_window(time.time())'),main.index('stdin.readline'))
        self.assertIn('admission_guard=require_paid_window',main)
