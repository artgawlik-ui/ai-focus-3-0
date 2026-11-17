"""Per-job Responses gateway. No model call without counted, reserved headroom.

The ledger is a conservative quota, NOT provider billing or the monthly Costs ledger.
The CLI never receives the real API key. Production entrypoint requires root and
an exclusive /run state directory; test servers use injected local transports.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
import time
from zoneinfo import ZoneInfo
from urllib.request import Request, HTTPRedirectHandler, build_opener

MAX_BODY = 262144
MAX_RESPONSE = 8 * 1024 * 1024
FIELDS = {'model', 'input', 'instructions', 'tools', 'tool_choice', 'text',
          'reasoning', 'parallel_tool_calls', 'include', 'store', 'stream',
          'max_output_tokens', 'service_tier', 'truncation', 'prompt_cache_key',
          'client_metadata'}
COUNT_FIELDS = {'model', 'input', 'instructions', 'tools', 'tool_choice',
                'text', 'reasoning', 'parallel_tool_calls', 'truncation'}


class Limit(Exception):
    pass


def integer(value, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise Limit('INVALID_LIMIT')
    return value


def money(value, maximum):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or not 0 < result <= Decimal(str(maximum)):
            raise ValueError()
        return result
    except (InvalidOperation, ValueError):
        raise Limit('INVALID_PRICE_OR_BUDGET') from None


def timestamp(value):
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.tzinfo is None:
            raise ValueError()
        return date.timestamp()
    except (AttributeError, TypeError, ValueError):
        raise Limit('INVALID_TARIFF_TIME') from None


def require_paid_window(wall):
    local = datetime.fromtimestamp(wall, timezone.utc).astimezone(ZoneInfo('Europe/Warsaw'))
    if not 9 <= local.hour < 18:
        raise Limit('PAID_EXECUTION_WINDOW_CLOSED')


class Policy:
    def __init__(self, raw, now=None):
        now = time.time() if now is None else now
        if raw.get('enabled') is not True or raw.get('schema') != 1:
            raise Limit('EXECUTOR_LIMIT_POLICY_NOT_APPROVED')
        model = raw.get('model')
        if not isinstance(model, str) or not re.fullmatch(r'[a-zA-Z0-9._-]{1,100}', model):
            raise Limit('APPROVED_MODEL_REQUIRED')
        self.model = model
        quote = raw.get('tariff', {})
        if (quote.get('service_tier') != 'default' or
            quote.get('source') != 'https://openai.com/api/pricing/' or
            not isinstance(quote.get('review_reference'), str) or
            not quote['review_reference'].startswith('https://github.com/artgawlik-ui/ai-focus-3-0/')):
            raise Limit('VERIFIED_TARIFF_REQUIRED')
        verified, expires = timestamp(quote.get('verified_at')), timestamp(quote.get('expires_at'))
        if not verified <= now < expires or expires - verified > 86400:
            raise Limit('TARIFF_EXPIRED_OR_FUTURE')
        self.expires = expires
        self.input_price = money(quote.get('input_usd_per_million'), 1000)
        self.output_price = money(quote.get('output_usd_per_million'), 1000)
        # Require an explicit reviewed count-endpoint ceiling, including zero
        # only when verified free. Never silently omit preflight API charges.
        try:
            fee = Decimal(str(quote.get('max_count_usd_per_request')))
            if not fee.is_finite() or not 0 <= fee <= 2:
                raise ValueError()
            self.count_fee = int((fee * 1_000_000_000).to_integral_value(
                rounding=ROUND_CEILING))
        except (InvalidOperation, ValueError):
            raise Limit('COUNT_ENDPOINT_PRICE_REQUIRED') from None
        self.budget = int(money(raw.get('max_usd'), 2) * 1_000_000_000)
        self.requests = integer(raw.get('max_requests'), 5)
        self.input_tokens = integer(raw.get('max_input_tokens_per_request'), 60000)
        self.output_tokens = integer(raw.get('max_output_tokens_per_request'), 4096)
        self.total_tokens = integer(raw.get('max_total_reserved_tokens'), 200000)
        self.tpm = integer(raw.get('max_reserved_tokens_per_minute'), 60000)
        self.seconds = integer(raw.get('max_seconds'), 600)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Limit('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def decode(data):
    try:
        return json.loads(data, object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(Limit('INVALID_JSON')))
    except (ValueError, UnicodeError, RecursionError):
        raise Limit('INVALID_JSON') from None


def normalize(body, policy):
    if not isinstance(body, dict) or set(body) - FIELDS:
        raise Limit('UNSUPPORTED_REQUEST')
    if body.get('model') != policy.model or 'input' not in body:
        raise Limit('MODEL_OR_INPUT_REJECTED')
    if body.get('service_tier', 'default') not in ('default', None):
        raise Limit('SERVICE_TIER_REJECTED')
    reasoning = body.get('reasoning')
    if reasoning is not None and (not isinstance(reasoning, dict) or
        reasoning.get('mode') not in (None, 'standard')):
        raise Limit('REASONING_MODE_REJECTED')
    # Only client-executed tools, optionally grouped once under a namespace.
    # No hosted tools, external state, media, files or compaction.
    tools = body.get('tools', [])
    def local_tool(tool, namespace=True):
        if not isinstance(tool, dict):
            return False
        if tool.get('type') in ('function', 'custom'):
            return True
        if namespace and tool.get('type') == 'namespace':
            children = tool.get('tools')
            return (isinstance(children, list) and bool(children) and
                    all(local_tool(child, namespace=False) for child in children))
        return False
    if not isinstance(tools, list) or not all(local_tool(tool) for tool in tools):
        raise Limit('HOSTED_OR_UNKNOWN_TOOL_REJECTED')
    denied_types = {'input_image', 'input_audio', 'input_file', 'compaction',
                    'item_reference', 'image_generation_call'}
    def inspect(value):
        if isinstance(value, dict):
            if isinstance(value.get('type'), str) and value['type'] in denied_types:
                raise Limit('OPAQUE_OR_MEDIA_INPUT_REJECTED')
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(body)
    clean = dict(body)
    # Native CLI trace metadata is not model history. Do not forward it to either
    # endpoint or persist it; counting and generation receive the same context.
    clean.pop('client_metadata', None)
    # Enforce on the wire, regardless of CLI config or task instructions.
    clean['max_output_tokens'] = policy.output_tokens
    clean['service_tier'] = 'default'
    clean['store'] = False
    clean['truncation'] = 'disabled'
    return clean


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OpenAI:
    """Fixed origin; no redirects, arbitrary URLs, environment proxies or retry."""
    def __init__(self, key):
        from urllib.request import ProxyHandler
        self.key = key
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def post(self, endpoint, body, timeout):
        if endpoint not in ('input_tokens', 'generate'):
            raise Limit('ENDPOINT_REJECTED')
        suffix = '/input_tokens' if endpoint == 'input_tokens' else ''
        request = Request('https://api.openai.com/v1/responses' + suffix,
                          data=json.dumps(body, ensure_ascii=False).encode(),
                          headers={'Authorization': 'Bearer ' + self.key,
                                   'Content-Type': 'application/json'}, method='POST')
        with self.opener.open(request, timeout=timeout) as response:
            data = response.read(MAX_RESPONSE + 1)
            if len(data) > MAX_RESPONSE:
                raise Limit('UPSTREAM_RESPONSE_TOO_LARGE')
            return response.headers.get('Content-Type', 'application/json'), data


class Gateway:
    def __init__(self, policy, upstream, state_dir, clock=time.monotonic, wall=time.time, admission_guard=None):
        self.admission_guard = admission_guard
        self.policy, self.upstream = policy, upstream
        self.clock, self.wall = clock, wall
        self.started = clock()
        self.lock = threading.Lock()
        # Exclusive creation prevents accidental restart/reset of a run allowance.
        self.directory = Path(state_dir)
        self.directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.records = []
        self.count_records = []
        self.stopped = False
        self.save()

    def save(self):
        ledger = {'schema': 1, 'stopped': self.stopped, 'requests': len(self.records),
                  'reserved_tokens': sum(r['tokens'] for r in self.records),
                  'reserved_nusd': sum(r['nusd'] for r in self.records) +
                      sum(r['nusd'] for r in self.count_records),
                  'count_requests': len(self.count_records),
                  'count_reservations': self.count_records,
                  'reservations': self.records}
        temporary = self.directory / 'ledger.tmp'
        with temporary.open('w', encoding='utf-8') as file:
            json.dump(ledger, file, separators=(',', ':'))
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, self.directory / 'ledger.json')
        descriptor = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def remaining(self):
        return self.policy.seconds - (self.clock() - self.started)

    def stop(self, reason):
        self.stopped = True
        self.save()
        raise Limit(reason)

    def exchange(self, data):
        # One count/reserve/generate transaction at a time across all callers.
        with self.lock:
            if self.stopped:
                raise Limit('EXECUTOR_STOPPED')
            try:
                if self.remaining() <= 0 or self.wall() >= self.policy.expires:
                    self.stop('DEADLINE_OR_TARIFF_EXPIRED')
                if len(data) > MAX_BODY:
                    self.stop('REQUEST_TOO_LARGE')
                body = normalize(decode(data), self.policy)
                if len(self.records) >= self.policy.requests:
                    self.stop('REQUEST_LIMIT')
                if self.admission_guard:
                    self.admission_guard(self.wall())
                counting = {k: v for k, v in body.items() if k in COUNT_FIELDS}
                committed = sum(r['nusd'] for r in self.records + self.count_records)
                if committed + self.policy.count_fee > self.policy.budget:
                    self.stop('COUNT_COST_CEILING')
                self.count_records.append({'nusd': self.policy.count_fee})
                self.save()  # Reserve preflight API allowance before sending it.
                _, counted = self.upstream.post('input_tokens', counting,
                                                min(20, self.remaining()))
                count = decode(counted)
                tokens = count.get('input_tokens') if isinstance(count, dict) else None
                if (not isinstance(count, dict) or count.get('object') != 'response.input_tokens'
                    or type(tokens) is not int or tokens < 0):
                    self.stop('INPUT_COUNT_MISSING')
                if tokens > self.policy.input_tokens:
                    self.stop('INPUT_TOKEN_LIMIT')
                if self.remaining() <= 0 or self.wall() >= self.policy.expires:
                    self.stop('DEADLINE_OR_TARIFF_EXPIRED')
                reserved = tokens + self.policy.output_tokens
                nusd = int(((tokens * self.policy.input_price +
                             self.policy.output_tokens * self.policy.output_price)
                            * 1000).to_integral_value(rounding=ROUND_CEILING))
                if sum(r['tokens'] for r in self.records) + reserved > self.policy.total_tokens:
                    self.stop('TOTAL_TOKEN_LIMIT')
                now = self.clock()
                if sum(r['tokens'] for r in self.records if now - r['at'] < 60) + reserved > self.policy.tpm:
                    self.stop('TPM_LIMIT')
                if sum(r['nusd'] for r in self.records + self.count_records) + nusd > self.policy.budget:
                    self.stop('COST_CEILING')
                if self.admission_guard:
                    self.admission_guard(self.wall())
                # Durable conservative reservation BEFORE the potentially paid POST.
                # Never refund on errors, disconnects, missing usage or short output.
                self.records.append({'at': now, 'tokens': reserved, 'nusd': nusd,
                                     'request_sha256': hashlib.sha256(data).hexdigest()})
                self.save()
                result = self.upstream.post('generate', body, min(60, self.remaining()))
                # No content, credentials, response bodies or customer data in ledger/logs.
                if self.remaining() <= 0:
                    self.stop('DEADLINE_EXCEEDED')
                return result
            except Limit:
                if not self.stopped:
                    self.stopped = True
                    self.save()
                raise
            except Exception:
                self.stopped = True
                self.save()
                raise Limit('UPSTREAM_OR_LEDGER_FAILURE') from None


def server(gateway, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log request content or auth headers.

        def do_POST(self):
            self.connection.settimeout(5)
            try:
                if self.path != '/responses' or self.headers.get('Transfer-Encoding'):
                    raise Limit('ROUTE_OR_ENCODING_REJECTED')
                if self.headers.get('Content-Encoding') not in (None, 'identity'):
                    raise Limit('ENCODING_REJECTED')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY:
                    raise Limit('REQUEST_TOO_LARGE')
                data = self.rfile.read(length)
                if len(data) != length:
                    raise Limit('TRUNCATED_REQUEST')
                content_type, response = gateway.exchange(data)
                status = 200
            except Exception as exc:
                code = str(exc) if isinstance(exc, Limit) else 'GATEWAY_REQUEST_FAILURE'
                response = json.dumps({'error': {'type': 'focus_executor_limit',
                                                 'code': code}}).encode()
                content_type, status = 'application/json', 429
            try:
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(response)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(response)
            except OSError:
                pass
            self.close_connection = True
    instance = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    instance.daemon_threads = True
    return instance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--policy', required=True)
    parser.add_argument('--state-dir', required=True)
    args = parser.parse_args()
    if os.geteuid() != 0 or not args.state_dir.startswith('/run/focus-codex-'):
        raise Limit('ROOT_PRIVATE_STATE_REQUIRED')
    policy = Policy(decode(Path(args.policy).read_bytes()))
    require_paid_window(time.time())
    key = __import__('sys').stdin.readline(512).strip()
    if not key or len(key) >= 511:
        raise Limit('API_AUTH_MISSING')
    gateway = Gateway(policy, OpenAI(key), args.state_dir, admission_guard=require_paid_window)
    listener = server(gateway, 8765)
    # Independent lifetime; later action steps cannot restart/reset its ledger.
    timer = threading.Timer(policy.seconds, listener.shutdown)
    timer.daemon = True
    timer.start()
    print('EXECUTOR_LIMIT_GATE_READY', flush=True)
    listener.serve_forever(poll_interval=0.1)
    listener.server_close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('BLOCKED: ' + (str(exc) if isinstance(exc, Limit) else
                            'EXECUTOR_LIMIT_GATE_FAILURE'))
        raise SystemExit(1)
