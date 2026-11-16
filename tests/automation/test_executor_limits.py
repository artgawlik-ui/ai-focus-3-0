"""Offline quota, failure, concurrency and loopback HTTP tests. No OpenAI calls."""
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from scripts.codex_automation.executor_limits import (
    Gateway, Limit, Policy, OpenAI, normalize, server,
)

NOW = 1805400000


def policy(**changes):
    raw = {
        'schema': 1, 'enabled': True, 'model': 'synthetic-model',
        'tariff': {'service_tier': 'default',
                   'source': 'https://openai.com/api/pricing/',
                   'review_reference': 'https://github.com/artgawlik-ui/ai-focus-3-0/pull/27',
                   'verified_at': '2026-11-16T00:00:00Z',
                   'expires_at': '2026-11-17T00:00:00Z',
                   'input_usd_per_million': '1',
                   'output_usd_per_million': '1'},
        'max_usd': '0.001', 'max_requests': 2,
        'max_input_tokens_per_request': 100,
        'max_output_tokens_per_request': 20,
        'max_total_reserved_tokens': 1000,
        'max_reserved_tokens_per_minute': 500,
        'max_seconds': 60,
    }
    raw.update(changes)
    # Fixed UTC inside the fixture tariff validity; no production rates/model.
    return Policy(raw, now=1794830400)


class Fake:
    def __init__(self, tokens=10, failure=None):
        self.tokens, self.failure, self.calls = tokens, failure, []

    def post(self, endpoint, body, timeout):
        self.calls.append((endpoint, copy.deepcopy(body)))
        if endpoint == 'input_tokens':
            return 'application/json', json.dumps(
                {'object': 'response.input_tokens', 'input_tokens': self.tokens}).encode()
        if self.failure:
            raise self.failure
        return 'text/event-stream', b'data: {"type":"response.completed"}\n\n'


class LimitsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.tick = 0
        self.now = 1794830400
        self.fake = Fake()

    def gate(self, fake=None, **limits):
        return Gateway(policy(**limits), fake or self.fake,
                       Path(self.temporary.name) / 'run',
                       clock=lambda: self.tick, wall=lambda: self.now)

    def request(self, **updates):
        body = {'model': 'synthetic-model', 'input': 'synthetic code task',
                'stream': True}
        body.update(updates)
        return json.dumps(body).encode()

    def blocked(self, gate, expected, data=None):
        with self.assertRaisesRegex(Limit, '^' + expected + '$'):
            gate.exchange(data if data is not None else self.request())

    def test_output_cap_is_enforced_on_wire_not_prompt(self):
        gate = self.gate()
        gate.exchange(self.request(max_output_tokens=999999, service_tier='default'))
        sent = self.fake.calls[-1][1]
        self.assertEqual(sent['max_output_tokens'], 20)
        self.assertEqual(sent['service_tier'], 'default')
        self.assertFalse(sent['store'])
        self.assertEqual(sent['truncation'], 'disabled')
        self.assertEqual(gate.records[0]['tokens'], 30)
        self.assertEqual(gate.records[0]['nusd'], 30000)

    def test_request_limit_blocks_paid_post(self):
        gate = self.gate()
        gate.exchange(self.request())
        gate.exchange(self.request())
        self.blocked(gate, 'REQUEST_LIMIT')
        self.assertEqual([c[0] for c in self.fake.calls].count('generate'), 2)

    def test_cost_exact_boundary_and_no_refund(self):
        gate = self.gate(max_usd='0.00003')
        gate.exchange(self.request())
        self.blocked(gate, 'COST_CEILING')
        self.assertEqual(len(gate.records), 1)

    def test_total_token_limit(self):
        gate = self.gate(max_total_reserved_tokens=30)
        gate.exchange(self.request())
        self.blocked(gate, 'TOTAL_TOKEN_LIMIT')
        self.assertEqual([c[0] for c in self.fake.calls].count('generate'), 1)

    def test_tpm_limit(self):
        gate = self.gate(max_reserved_tokens_per_minute=30)
        gate.exchange(self.request())
        self.blocked(gate, 'TPM_LIMIT')

    def test_tpm_window_ages_but_total_quota_never_resets(self):
        gate = self.gate(max_reserved_tokens_per_minute=30, max_seconds=120)
        gate.exchange(self.request())
        self.tick = 61
        gate.exchange(self.request())
        self.assertEqual(sum(r['tokens'] for r in gate.records), 60)

    def test_oversized_input_never_generates(self):
        gate = self.gate(fake=Fake(tokens=101))
        self.blocked(gate, 'INPUT_TOKEN_LIMIT')
        self.assertFalse(gate.records)

    def test_missing_or_bad_counts_stop_before_generation(self):
        for count in (True, -1, '10', None):
            with self.subTest(count=count):
                fake = Fake(tokens=count)
                with tempfile.TemporaryDirectory() as temp:
                    gate = Gateway(policy(), fake, Path(temp) / 'run',
                                   wall=lambda: self.now)
                    self.blocked(gate, 'INPUT_COUNT_MISSING')
                    self.assertEqual([c[0] for c in fake.calls], ['input_tokens'])

    def test_bad_count_object(self):
        fake = Fake()
        fake.post = lambda *args: ('application/json', b'{"input_tokens":10}')
        gate = self.gate(fake=fake)
        self.blocked(gate, 'INPUT_COUNT_MISSING')

    def test_ambiguous_generation_failure_keeps_reservation_and_stops(self):
        fake = Fake(failure=TimeoutError('must not leak'))
        gate = self.gate(fake=fake)
        self.blocked(gate, 'UPSTREAM_OR_LEDGER_FAILURE')
        self.blocked(gate, 'EXECUTOR_STOPPED')
        ledger = json.loads((gate.directory / 'ledger.json').read_text())
        self.assertEqual(ledger['reserved_nusd'], 30000)
        self.assertEqual(ledger['requests'], 1)
        self.assertTrue(ledger['stopped'])

    def test_ledger_write_failure_never_generates(self):
        gate = self.gate()
        with patch.object(gate, 'save', side_effect=OSError('disk unavailable')):
            with self.assertRaises(Exception):
                gate.exchange(self.request())
        self.assertEqual([c[0] for c in self.fake.calls], ['input_tokens'])
        self.assertTrue(gate.stopped)

    def test_deadline_before_request(self):
        gate = self.gate()
        self.tick = 60
        self.blocked(gate, 'DEADLINE_OR_TARIFF_EXPIRED')
        self.assertFalse(self.fake.calls)

    def test_deadline_rechecked_after_counting(self):
        fake = Fake()
        original = fake.post
        def count_slow(*args):
            result = original(*args)
            self.tick = 61
            return result
        fake.post = count_slow
        gate = self.gate(fake=fake)
        self.blocked(gate, 'DEADLINE_OR_TARIFF_EXPIRED')
        self.assertFalse(gate.records)

    def test_expired_tariff_never_counts_or_generates(self):
        gate = self.gate()
        self.now += 86400
        self.blocked(gate, 'DEADLINE_OR_TARIFF_EXPIRED')
        self.assertFalse(self.fake.calls)

    def test_exclusive_state_directory_cannot_reset_allowance(self):
        gate = self.gate()
        gate.exchange(self.request())
        with self.assertRaises(FileExistsError):
            Gateway(policy(), Fake(), gate.directory)
        self.assertEqual(len(gate.records), 1)

    def test_concurrent_callers_share_single_budget(self):
        gate = self.gate(max_usd='0.00003', max_requests=5)
        def call(_):
            try:
                gate.exchange(self.request())
                return 'ok'
            except Limit:
                return 'blocked'
        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(call, range(5)))
        self.assertEqual(results.count('ok'), 1)
        self.assertEqual([c[0] for c in self.fake.calls].count('generate'), 1)

    def test_unapproved_model_and_hosted_tools_and_opaque_input(self):
        cases = [
            ({'model': 'other'}, 'MODEL_OR_INPUT_REJECTED'),
            ({'tools': [{'type': 'web_search'}]}, 'HOSTED_OR_UNKNOWN_TOOL_REJECTED'),
            ({'tools': [{'type': 'mcp'}]}, 'HOSTED_OR_UNKNOWN_TOOL_REJECTED'),
            ({'input': [{'type': 'input_image', 'image_url': 'https://example.invalid'}]},
             'OPAQUE_OR_MEDIA_INPUT_REJECTED'),
            ({'input': [{'type': 'reasoning', 'encrypted_content': 'opaque'}]},
             'OPAQUE_OR_MEDIA_INPUT_REJECTED'),
            ({'previous_response_id': 'external'}, 'UNSUPPORTED_REQUEST'),
            ({'service_tier': 'priority'}, 'SERVICE_TIER_REJECTED'),
            ({'background': True}, 'UNSUPPORTED_REQUEST'),
        ]
        for update, error in cases:
            with self.subTest(update=update):
                with tempfile.TemporaryDirectory() as temp:
                    fake = Fake()
                    gate = Gateway(policy(), fake, Path(temp) / 'run', wall=lambda: self.now)
                    self.blocked(gate, error, self.request(**update))
                    self.assertFalse(fake.calls)

    def test_duplicate_keys_and_oversized_body_rejected(self):
        gate = self.gate()
        self.blocked(gate, 'DUPLICATE_JSON_KEY', b'{"model":"a","model":"b"}')
        self.assertFalse(self.fake.calls)

    def test_count_contains_full_history_tools_and_instructions(self):
        gate = self.gate()
        gate.exchange(self.request(input=[{'role': 'user', 'content': 'history'}],
                                   instructions='system text',
                                   tools=[{'type': 'function', 'name': 'shell',
                                           'parameters': {'type': 'object'}}]))
        counted = self.fake.calls[0][1]
        sent = self.fake.calls[1][1]
        for key in ('model', 'input', 'instructions', 'tools'):
            self.assertEqual(counted[key], sent[key])

    def test_raw_prompt_secret_and_response_not_persisted(self):
        gate = self.gate()
        gate.exchange(self.request(input='SYNTHETIC_PRIVATE_MARKER'))
        ledger = (gate.directory / 'ledger.json').read_text()
        self.assertNotIn('SYNTHETIC_PRIVATE_MARKER', ledger)
        self.assertNotIn('response.completed', ledger)

    def test_default_checked_in_policy_is_disabled(self):
        raw = json.loads(Path('scripts/codex_automation/executor-limits.json').read_text())
        with self.assertRaisesRegex(Limit, 'EXECUTOR_LIMIT_POLICY_NOT_APPROVED'):
            Policy(raw)

    def test_invalid_unbounded_or_negative_policy_rejected(self):
        for update in ({'max_requests': 6}, {'max_seconds': 601}, {'max_usd': '2.01'},
                       {'max_usd': 'NaN'}, {'max_usd': '-1'},
                       {'max_output_tokens_per_request': True}):
            with self.subTest(update=update), self.assertRaises(Limit):
                policy(**update)

    def test_live_transport_has_fixed_origin_and_no_redirect_or_proxy(self):
        upstream = OpenAI('synthetic-test-key')
        class Response:
            headers = {'Content-Type': 'application/json'}
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, count): return b'{"input_tokens":10}'
        with patch.object(upstream.opener, 'open', return_value=Response()) as opened:
            upstream.post('input_tokens', {'model': 'synthetic'}, 1)
            request = opened.call_args.args[0]
            self.assertEqual(request.full_url, 'https://api.openai.com/v1/responses/input_tokens')
            self.assertEqual(request.get_header('Authorization'), 'Bearer synthetic-test-key')
        with self.assertRaisesRegex(Limit, 'ENDPOINT_REJECTED'):
            upstream.post('https://example.invalid', {}, 1)

    def test_loopback_http_reaches_gateway_and_blocks_next_paid_call(self):
        gate = self.gate(max_usd='0.00003')
        http = server(gate, 0)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        try:
            origin = 'http://127.0.0.1:' + str(http.server_port)
            request = Request(origin + '/responses', data=self.request(),
                              headers={'Content-Type': 'application/json'}, method='POST')
            with urlopen(request, timeout=2) as response:
                self.assertIn(b'response.completed', response.read())
            with self.assertRaises(HTTPError) as failure:
                urlopen(request, timeout=2)
            self.assertIn(b'COST_CEILING', failure.exception.read())
            self.assertEqual([c[0] for c in self.fake.calls].count('generate'), 1)
            bad = Request(origin + '/responses/compact', data=self.request(), method='POST')
            with self.assertRaises(HTTPError) as failure:
                urlopen(bad, timeout=2)
            self.assertIn(b'ROUTE_OR_ENCODING_REJECTED', failure.exception.read())
        finally:
            http.shutdown()
            http.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
