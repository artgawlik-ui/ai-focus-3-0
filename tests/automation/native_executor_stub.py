"""CI-only real CLI contract probe. Synthetic SSE; no OpenAI transport or key."""
from datetime import datetime, timedelta, timezone
import json
import os
import threading
from scripts.codex_automation.executor_limits import Gateway, Limit, Policy, server


class OfflineProvider:
    def post(self, endpoint, body, timeout):
        if endpoint == 'input_tokens':
            return 'application/json', b'{"object":"response.input_tokens","input_tokens":42}'
        if endpoint != 'generate':
            raise AssertionError('Unexpected offline endpoint')
        if body['max_output_tokens'] != 2048 or body['service_tier'] != 'default':
            raise AssertionError('Gateway did not impose limits')
        message = {'type': 'message', 'role': 'assistant', 'id': 'msg_offline',
                   'phase': 'final_answer',
                   'content': [{'type': 'output_text', 'text': 'OFFLINE_EXECUTOR_PASS'}]}
        events = [
            {'type': 'response.created', 'response': {'id': 'resp_offline'}},
            {'type': 'response.output_item.done', 'item': message},
            {'type': 'response.completed', 'response': {
                'id': 'resp_offline', 'usage': {'input_tokens': 42,
                    'output_tokens': 8, 'total_tokens': 50}}},
        ]
        response = ''.join('event: ' + event['type'] + '\ndata: ' +
                           json.dumps(event) + '\n\n' for event in events)
        return 'text/event-stream', response.encode()


class OfflineGateway(Gateway):
    def exchange(self, data):
        try:
            return super().exchange(data)
        except Limit as error:
            # CI fixture only: fixed error code and protocol field names, no values.
            body = json.loads(data)
            keys = sorted(body) if isinstance(body, dict) else []
            types = [tool.get('type') for tool in body.get('tools', []) if isinstance(tool, dict)]
            print('OFFLINE_REJECT: ' + str(error) + ' keys=' + repr(keys) +
                  ' tool_types=' + repr(types), flush=True)
            raise


def main():
    if os.geteuid() != 0 or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('CI root probe only')
    now = datetime.now(timezone.utc)
    raw = {'schema': 1, 'enabled': True, 'model': 'gpt-5.1-codex-mini',
           'tariff': {'service_tier': 'default',
                      'source': 'https://openai.com/api/pricing/',
                      'review_reference': 'https://github.com/artgawlik-ui/ai-focus-3-0/pull/27',
                      'verified_at': (now - timedelta(seconds=10)).isoformat(),
                      'expires_at': (now + timedelta(minutes=10)).isoformat(),
                      'input_usd_per_million': '1', 'output_usd_per_million': '1',
                      'max_count_usd_per_request': '0'},
           'max_usd': '0.01', 'max_requests': 1,
           'max_input_tokens_per_request': 24000,
           'max_output_tokens_per_request': 2048,
           'max_total_reserved_tokens': 60000,
           'max_reserved_tokens_per_minute': 30000,
           'max_seconds': 600}
    # These are synthetic prices/counts. This class cannot call external API.
    gateway = OfflineGateway(Policy(raw), OfflineProvider(), '/run/focus-codex-offline-probe')
    listener = server(gateway, 8765)
    timer = threading.Timer(600, listener.shutdown)
    timer.daemon = True
    timer.start()
    print('OFFLINE_GATE_READY', flush=True)
    listener.serve_forever(poll_interval=0.1)
    listener.server_close()


if __name__ == '__main__':
    main()
