"""Production entrypoint contract with synthetic receipts/provider; no external API.

OS identity, files and listener are isolated fixtures. Receipt authentication,
policy validation, admission and the quota ledger execute their production code.
Native root/CLI isolation is tested separately by native-executor-offline in CI.
"""
from contextlib import ExitStack
import copy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.codex_automation import executor_limits as limits
from scripts.codex_automation import github_budget_transport as transport
from scripts.codex_automation import pipeline
from tests.automation import test_executor_admission as binding_fixtures
from tests.automation.test_executor_limits import Fake
from tests.automation.test_github_budget_transport import API, BASE, payload


class StartupContractTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name) / 'state'
        self.api = API()
        self.api.statuses = [dict(
            context=transport.context(payload()), state='success',
            creator={'login': transport.RECEIPT_LOGIN},
            target_url=f'https://github.com/{pipeline.REPO}/actions/runs/123',
            description='Private budget reservation committed')]
        self.env = binding_fixtures.AdmissionBindingTests().env()
        self.provider = Fake()
        self.key = Mock(wraps=StringIO('synthetic-only-not-an-api-key\n'))
        self.events = []
        self.gateway = None

    def start(self, *, now=1794830400, disabled=False):
        raw = json.loads((Path(__file__).resolve().parents[2] /
                          'scripts/codex_automation/executor-limits.json').read_text())
        # Deliberately synthetic model and prices; never approval for paid use.
        raw.update(enabled=not disabled, model='synthetic-model', max_requests=1,
                   max_input_tokens_per_request=100, max_output_tokens_per_request=20)
        raw['tariff'] = dict(service_tier='default',
            source='https://openai.com/api/pricing/',
            review_reference=f'https://github.com/{pipeline.REPO}/pull/62',
            verified_at='2026-11-16T00:00:00Z', expires_at='2026-11-17T00:00:00Z',
            input_usd_per_million='1', output_usd_per_million='1',
            max_count_usd_per_request='0')
        files = {'fixture-policy.json': json.dumps(raw).encode(),
                 'budget-request/request.json': json.dumps(payload()).encode()}
        def read_bytes(path):
            return files[str(path)]  # Unexpected file access fails closed.
        def provider(key):
            self.events.append('key')
            self.assertEqual(key, 'synthetic-only-not-an-api-key')
            self.assertEqual(len(self.api.calls), 1)
            self.assertEqual(self.api.calls[0][0], 'GET')
            self.assertIn('/commits/'+BASE+'/statuses?', self.api.calls[0][1])
            return self.provider
        real_gateway = limits.Gateway
        def gateway(pol, upstream, state_dir, **kwargs):
            self.assertEqual(state_dir, '/run/focus-codex-123-1')
            self.gateway = real_gateway(pol, upstream, self.state,
                wall=lambda: now, **kwargs)
            return self.gateway
        listener = Mock()
        def serve(**kwargs):
            self.events.append('serve')
            data = json.dumps(dict(model='synthetic-model', input='offline')).encode()
            self.gateway.exchange(data)
            with self.assertRaisesRegex(limits.Limit, 'REQUEST_LIMIT'):
                self.gateway.exchange(data)
        listener.serve_forever.side_effect = serve
        with ExitStack() as stack:
            for target, kwargs in [
                ('sys.argv', dict(new=['executor', '--policy', 'fixture-policy.json',
                                     '--state-dir', '/run/focus-codex-123-1'])),
                ('sys.stdin', dict(new=self.key)),
                ('sys.stdout', dict(new=StringIO())),
                ('os.geteuid', dict(return_value=0)),
                ('pathlib.Path.read_bytes', dict(new=read_bytes)),
            ]:
                stack.enter_context(patch(target, **kwargs))
            stack.enter_context(patch.dict('os.environ', self.env, clear=True))
            stack.enter_context(patch.object(limits.time, 'time', return_value=now))
            stack.enter_context(patch.object(pipeline, 'API', return_value=self.api))
            stack.enter_context(patch.object(limits, 'OpenAI', side_effect=provider))
            stack.enter_context(patch.object(limits, 'Gateway', side_effect=gateway))
            stack.enter_context(patch.object(limits, 'server', return_value=listener))
            stack.enter_context(patch.object(limits.threading, 'Timer'))
            limits.main()
        return listener

    def assert_no_key_or_listener(self):
        self.key.readline.assert_not_called()
        self.assertEqual(self.events, [])
        self.assertFalse(self.state.exists())
        self.assertEqual(self.provider.calls, [])

    def test_exact_receipt_precedes_key_then_real_quota_blocks_second_request(self):
        listener = self.start()
        self.assertEqual(self.events, ['key', 'serve'])
        self.assertEqual([call[0] for call in self.provider.calls], ['input_tokens', 'generate'])
        ledger = json.loads((self.state / 'ledger.json').read_text())
        self.assertEqual(ledger['requests'], 1)
        self.assertTrue(ledger['stopped'])
        listener.server_close.assert_called_once()

    def test_forged_or_failed_receipt_cannot_read_key(self):
        original = copy.deepcopy(self.api.statuses[0])
        for changes in ({'creator': {'login': 'untrusted'}}, {'state': 'failure'},
                        {'target_url': original['target_url']+'0'},
                        {'description': 'Different reservation'}):
            with self.subTest(changes=changes):
                self.api.statuses = [dict(original, **changes)]
                with self.assertRaisesRegex(transport.TransportBlocked, 'INVALID_PRIVATE_RECEIPT'):
                    self.start()
                self.assert_no_key_or_listener()

    def test_different_run_context_cannot_read_key(self):
        self.env['GITHUB_RUN_ID'] = '124'
        with self.assertRaisesRegex(transport.TransportBlocked, 'CONTEXT_MISMATCH'):
            self.start()
        self.assertEqual(self.api.calls, [])
        self.assert_no_key_or_listener()

    def test_closed_window_cannot_lookup_receipt_or_read_key(self):
        with self.assertRaisesRegex(limits.Limit, 'PAID_EXECUTION_WINDOW_CLOSED'):
            self.start(now=1794848400)  # 18:00 Warsaw, inside fixture tariff validity.
        self.assertEqual(self.api.calls, [])
        self.assert_no_key_or_listener()

    def test_disabled_profile_cannot_lookup_receipt_or_read_key(self):
        with self.assertRaisesRegex(limits.Limit, 'POLICY_NOT_APPROVED'):
            self.start(disabled=True)
        self.assertEqual(self.api.calls, [])
        self.assert_no_key_or_listener()

    def test_restart_cannot_reset_existing_ledger(self):
        self.start()
        before = (self.state / 'ledger.json').read_bytes()
        self.api.calls.clear()
        self.key = Mock(wraps=StringIO('synthetic-only-not-an-api-key\n'))
        with self.assertRaises(FileExistsError):
            self.start()
        self.assertEqual((self.state / 'ledger.json').read_bytes(), before)
        self.assertEqual([call[0] for call in self.provider.calls], ['input_tokens', 'generate'])
