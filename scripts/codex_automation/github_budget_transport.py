"""Outbound-only GitHub/private-budget protocol; explicit opt-in, no model calls.

Requests are immutable Actions artifacts, not executable instructions. Receipts
are commit statuses from a separately pinned controller identity. The private
controller polls GitHub; neither PostgreSQL nor the worker needs public ingress.
This candidate does not remove the workflow's final activation barrier.
"""
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import re
import secrets
import signal
import stat
import sys
import time
import threading
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from zipfile import ZipFile

try:
    from . import pipeline as policy
    from . import private_execution as lifecycle
    from .live_cost_gate import CostGateBlocked
    from .openai_costs import RejectRedirect
except ImportError:
    import pipeline as policy
    import private_execution as lifecycle
    from live_cost_gate import CostGateBlocked
    from openai_costs import RejectRedirect

PREFIX = '/repos/' + policy.REPO
WORKFLOW = '.github/workflows/codex-issues.yml'
RECEIPT_LOGIN = 'artgawlik-ui'  # separate owner-scoped PAT; never github-actions[bot]
MAX_ARCHIVE = 32768
MAX_REQUEST = 4096
FIELDS = {'version','repository','run_id','attempt','issue','comment_id','digest','base','nonce'}


class TransportBlocked(RuntimeError):
    """Only fixed safe codes may be logged."""


def opted_in(env):
    if env.get('FOCUS_PRIVATE_TRANSPORT_ENABLED') != 'true':
        raise TransportBlocked('PRIVATE_TRANSPORT_OFF')


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != FIELDS:
        raise TransportBlocked('INVALID_BUDGET_REQUEST')
    if (type(payload['version']) is not int or payload['version'] != 1 or
        payload['repository'] != policy.REPO or
        type(payload['attempt']) is not int or payload['attempt'] != 1 or
        any(type(payload[k]) is not int or not 0 < payload[k] < 10**20
            for k in ('run_id','issue','comment_id')) or
        not isinstance(payload['nonce'], str) or
        not re.fullmatch(r'[a-f0-9]{64}', payload['nonce'])):
        raise TransportBlocked('INVALID_BUDGET_REQUEST')
    task = lifecycle.ApprovedTask(payload['issue'], str(payload['run_id'])+':1',
                                  payload['digest'], payload['base'])
    task.validate()
    return task


def context(payload):
    validate(payload)
    return f"focus-budget/{payload['run_id']}/1/{payload['nonce']}"


def request_file(env=None):
    env = os.environ if env is None else env
    opted_in(env)
    if (env.get('GITHUB_REPOSITORY') != policy.REPO or
        env.get('GITHUB_REF') != 'refs/heads/main' or env.get('GITHUB_RUN_ATTEMPT') != '1'):
        raise TransportBlocked('TRUSTED_FIRST_ATTEMPT_REQUIRED')
    snapshot = policy.approved_snapshot()
    event = json.loads(Path(env['GITHUB_EVENT_PATH']).read_text())
    if event.get('action') != 'created' or event.get('issue', {}).get('number') != snapshot['number']:
        raise TransportBlocked('APPROVAL_EVENT_MISMATCH')
    payload = dict(version=1, repository=policy.REPO, run_id=int(env['GITHUB_RUN_ID']),
                   attempt=1, issue=snapshot['number'], comment_id=event['comment']['id'],
                   digest=snapshot['digest'], base=snapshot['base'], nonce=secrets.token_hex(32))
    validate(payload)
    Path('budget-request').mkdir(exist_ok=False)
    Path('budget-request/request.json').write_text(json.dumps(payload, separators=(',', ':')))
    return payload


def decode_archive(data):
    if not isinstance(data, bytes) or len(data) > MAX_ARCHIVE:
        raise TransportBlocked('ARTIFACT_SIZE_LIMIT')
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if (len(entries) != 1 or entries[0].filename != 'request.json' or
                entries[0].file_size > MAX_REQUEST or entries[0].flag_bits & 1 or
                stat.S_ISLNK(entries[0].external_attr >> 16)):
                raise TransportBlocked('ARTIFACT_LAYOUT_REJECTED')
            with archive.open(entries[0]) as stream:
                raw = stream.read(MAX_REQUEST + 1)
            if len(raw) > MAX_REQUEST:
                raise TransportBlocked('ARTIFACT_SIZE_LIMIT')
            # Duplicate JSON keys cannot silently replace trusted identity data.
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise TransportBlocked('DUPLICATE_REQUEST_FIELD')
                    result[key] = value
                return result
            payload = json.loads(raw, object_pairs_hook=unique)
        validate(payload)
        return payload
    except (TransportBlocked, lifecycle.ExecutionBlocked):
        raise
    except Exception:
        raise TransportBlocked('INVALID_ARTIFACT_ARCHIVE') from None


def download(api, artifact_id, *, opener=None):
    if type(artifact_id) is not int or artifact_id <= 0:
        raise TransportBlocked('INVALID_ARTIFACT_ID')
    opener = build_opener(RejectRedirect()).open if opener is None else opener
    url = f'https://api.github.com{PREFIX}/actions/artifacts/{artifact_id}/zip'
    req = Request(url, headers={'Authorization':'Bearer '+api.token,
                               'Accept':'application/vnd.github+json'})
    try:
        try:
            response = opener(req, timeout=20)
        except HTTPError as exc:
            if exc.code != 302:
                raise TransportBlocked('ARTIFACT_DOWNLOAD_UNAVAILABLE') from None
            location = exc.headers.get('Location', '')
            parsed = urlsplit(location)
            if (parsed.scheme != 'https' or parsed.username or parsed.password or
                parsed.port not in (None, 443) or parsed.fragment or
                not any((parsed.hostname or '').endswith(suffix) for suffix in
                        ('.blob.core.windows.net','.actions.githubusercontent.com'))):
                raise TransportBlocked('ARTIFACT_REDIRECT_REJECTED')
            # New Request: no Authorization forwarded to signed asset storage.
            response = opener(Request(location, headers={'Accept':'application/zip'}), timeout=20)
        with response:
            data = response.read(MAX_ARCHIVE + 1)
        if len(data) > MAX_ARCHIVE:
            raise TransportBlocked('ARTIFACT_SIZE_LIMIT')
        return data
    except TransportBlocked:
        raise
    except Exception:
        raise TransportBlocked('ARTIFACT_DOWNLOAD_UNAVAILABLE') from None


def verify_request(api, payload, *, trusted_sha, now=None):
    task = validate(payload)
    now = lifecycle.utc(now)
    if not isinstance(trusted_sha, str) or not policy.SHA.fullmatch(trusted_sha):
        raise TransportBlocked('PINNED_CONTROLLER_SHA_REQUIRED')
    run = api.call('GET', f"{PREFIX}/actions/runs/{payload['run_id']}")
    if (run.get('id') != payload['run_id'] or run.get('run_attempt') != 1 or
        run.get('event') != 'issue_comment' or run.get('path') != WORKFLOW or
        run.get('status') != 'in_progress' or run.get('head_branch') != 'main' or
        run.get('head_sha') != trusted_sha or task.base != trusted_sha or
        run.get('repository', {}).get('full_name') != policy.REPO or
        run.get('head_repository', {}).get('full_name') != policy.REPO):
        raise TransportBlocked('UNTRUSTED_WORKFLOW_RUN')
    try:
        started = datetime.fromisoformat(run['run_started_at'].replace('Z','+00:00'))
        if started.utcoffset() is None or not timedelta(0) <= now-started:
            raise ValueError()
    except Exception:
        raise TransportBlocked('STALE_WORKFLOW_REQUEST') from None
    # Environment review may take hours. Freshness belongs to the authenticated
    # active receipt-wait step (strict <90s), not time spent awaiting owner review.
    verify_waiting_job(api, payload, now=now)
    comment = api.call('GET', f"{PREFIX}/issues/comments/{payload['comment_id']}")
    if (comment.get('id') != payload['comment_id'] or
        comment.get('issue_url') != f'https://api.github.com{PREFIX}/issues/{task.issue}'):
        raise TransportBlocked('APPROVAL_COMMENT_MISMATCH')
    # Use the existing exact content digest, permission, current open issue and
    # rerun-actor policy against data fetched directly from authenticated GitHub.
    event = {'action':'created','repository':{'full_name':policy.REPO},
             'issue':{'number':task.issue},'comment':comment}
    approved = policy.authorize(event, api, run.get('actor', {}).get('login'),
                                run.get('triggering_actor', {}).get('login'))
    if policy.digest(approved) != task.digest:
        raise TransportBlocked('REQUEST_DIGEST_MISMATCH')
    policy.check_environment(api)
    ref = api.call('GET', f'{PREFIX}/git/ref/heads/codex/issue-{task.issue}')
    if ref.get('object', {}).get('sha') != task.base:
        raise TransportBlocked('ISSUE_CLAIM_MISMATCH')
    return task


def verify_waiting_job(api, payload, *, now=None):
    """Require a live trusted wait step, leaving 30s of its 120s timeout.

    Use GitHub job timestamps, never the issue/agent clock. Recompute wall time
    after the API read; production callers leave `now` unset.
    """
    result = api.call('GET', f"{PREFIX}/actions/runs/{payload['run_id']}/jobs?per_page=100")
    jobs = result.get('jobs')
    if (not isinstance(jobs, list) or result.get('total_count') != len(jobs) or
        len(jobs) > 100):
        raise TransportBlocked('INCOMPLETE_JOB_LIST')
    matches = [j for j in jobs if isinstance(j, dict) and j.get('name') == 'codex']
    if len(matches) != 1:
        raise TransportBlocked('ACTIVE_RECEIPT_WAIT_REQUIRED')
    job = matches[0]
    if (job.get('run_id') != payload['run_id'] or job.get('run_attempt') != 1 or
        job.get('head_sha') != payload['base'] or job.get('status') != 'in_progress'):
        raise TransportBlocked('ACTIVE_RECEIPT_WAIT_REQUIRED')
    steps = job.get('steps')
    if not isinstance(steps, list):
        raise TransportBlocked('ACTIVE_RECEIPT_WAIT_REQUIRED')
    waits = [s for s in steps if isinstance(s, dict) and
             s.get('name') == 'Wait for private PostgreSQL reservation receipt']
    if (len(waits) != 1 or waits[0].get('status') != 'in_progress' or
        waits[0].get('conclusion') is not None or waits[0].get('completed_at') is not None):
        raise TransportBlocked('ACTIVE_RECEIPT_WAIT_REQUIRED')
    try:
        started = datetime.fromisoformat(waits[0]['started_at'].replace('Z', '+00:00'))
        if started.utcoffset() is None or not timedelta(0) <= lifecycle.utc(now)-started < timedelta(seconds=90):
            raise ValueError()
    except Exception:
        raise TransportBlocked('RECEIPT_ADMISSION_WINDOW_CLOSED') from None


def handle_request(api, conn, payload, *, trusted_sha, now=None, reader=None, accepting=lambda: True):
    if api.call('GET', '/user').get('login') != RECEIPT_LOGIN:
        raise TransportBlocked('PRIVATE_CONTROLLER_IDENTITY_REQUIRED')
    task = verify_request(api, payload, trusted_sha=trusted_sha, now=now)
    # No success receipt is posted unless this exact run is durably reserved.
    # Re-delivery fails closed (no second receipt/paid run) rather than creating a
    # second hold. A lost receipt retains its hold for explicit reconciliation.
    if not accepting():
        raise TransportBlocked('CONTROLLER_DRAINING')
    def authorize(candidate):
        if candidate != task or not accepting():
            return False
        verify_waiting_job(api, payload, now=now)
        return True
    lifecycle.admit(conn, task=task, authorize=authorize,
                    now=now, reader=reader)
    # A job can end after commit. Withhold the receipt and retain its hold;
    # terminal GitHub evidence and genuine cost coverage govern reconciliation.
    verify_waiting_job(api, payload, now=now)
    if not accepting():
        raise TransportBlocked('CONTROLLER_DRAINING')
    receipt = api.call('POST', f'{PREFIX}/statuses/{task.base}', {
        'state':'success', 'context':context(payload),
        'description':'Private budget reservation committed',
        'target_url':f"https://github.com/{policy.REPO}/actions/runs/{payload['run_id']}"})
    if receipt.get('creator', {}).get('login') != RECEIPT_LOGIN:
        raise TransportBlocked('RECEIPT_IDENTITY_MISMATCH')
    return task


def wait_receipt(api, payload, *, timeout=120, clock=time.monotonic, sleep=time.sleep):
    validate(payload)
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise TransportBlocked('INVALID_RECEIPT_TIMEOUT')
    deadline = clock()+timeout
    expected = context(payload)
    while clock() < deadline:
        # Paginate boundedly; no receipt within the bounds means BLOCKED, never
        # infer success from the combined status or a different run's context.
        for page in range(1, 6):
            if clock() >= deadline:
                raise TransportBlocked('PRIVATE_RECEIPT_TIMEOUT')
            rows = api.call('GET', f"{PREFIX}/commits/{payload['base']}/statuses?per_page=100&page={page}")
            if clock() >= deadline:
                raise TransportBlocked('PRIVATE_RECEIPT_TIMEOUT')
            if not isinstance(rows, list):
                raise TransportBlocked('INVALID_RECEIPT_RESPONSE')
            for row in rows:
                if row.get('context') != expected:
                    continue
                if (row.get('creator', {}).get('login') != RECEIPT_LOGIN or
                    row.get('target_url') != f"https://github.com/{policy.REPO}/actions/runs/{payload['run_id']}" or
                    row.get('description') != 'Private budget reservation committed' or
                    row.get('state') != 'success'):
                    raise TransportBlocked('INVALID_PRIVATE_RECEIPT')
                return
            if len(rows) < 100:
                break
        sleep(min(5, max(0, deadline-clock())))
    raise TransportBlocked('PRIVATE_RECEIPT_TIMEOUT')


def poll_once(api, conn, *, trusted_sha, now=None, reader=None, downloader=download, accepting=lambda: True):
    runs = api.call('GET', f'{PREFIX}/actions/workflows/codex-issues.yml/runs?event=issue_comment&status=in_progress&per_page=10')
    for run in runs.get('workflow_runs', []):
        run_id = run.get('id')
        if type(run_id) is not int or run_id < 1:
            raise TransportBlocked('INVALID_RUN_LIST')
        result = api.call('GET', f'{PREFIX}/actions/runs/{run_id}/artifacts?per_page=100')
        artifacts = result.get('artifacts', [])
        if result.get('total_count') != len(artifacts) or len(artifacts) > 100:
            raise TransportBlocked('INCOMPLETE_ARTIFACT_LIST')
        requests = [a for a in artifacts if a.get('name') == f'budget-request-{run_id}-1']
        if not requests:
            continue
        if len(requests) != 1 or requests[0].get('expired') is not False:
            raise TransportBlocked('AMBIGUOUS_REQUEST_ARTIFACT')
        payload = decode_archive(downloader(api, requests[0]['id']))
        if payload['run_id'] != run_id:
            raise TransportBlocked('ARTIFACT_RUN_MISMATCH')
        handle_request(api, conn, payload, trusted_sha=trusted_sha, now=now, reader=reader,
                       accepting=accepting)
        return 1  # at most one reservation per explicit poll
    return 0


def observe_finish(api, conn, *, task, now=None):
    task.validate()
    run_id = int(task.run_id.split(':')[0])
    run = api.call('GET', f'{PREFIX}/actions/runs/{run_id}')
    if (run.get('id') != run_id or run.get('run_attempt') != 1 or
        run.get('head_sha') != task.base or run.get('path') != WORKFLOW or
        run.get('repository', {}).get('full_name') != policy.REPO):
        raise TransportBlocked('FINISH_RUN_MISMATCH')
    if run.get('status') != 'completed':
        raise TransportBlocked('WORKFLOW_NOT_COMPLETED')
    outcome = {'success':'success','failure':'failure','cancelled':'cancelled'}.get(
        run.get('conclusion'), 'unknown')
    # Observing a terminal GitHub run is trusted finish evidence. Use observation
    # time conservatively, not an agent-provided completion timestamp. Holds stay.
    lifecycle.finish(conn, task=task, outcome=outcome, now=now)


def refresh_runs(api, conn, *, now=None, reader=None):
    """Recover finish from GitHub after cancellation/crash; never expire a hold."""
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute('SELECT e.run_id,e.issue_number,e.task_digest,e.base_sha,e.state '
                        "FROM codex_execution_runs e WHERE e.state <> 'reconciled'")
            rows = cur.fetchall()
    # Above read transaction is closed before lifecycle transactions or receipts.
    ready = True
    for run_id, issue, digest, base, state in rows:
        task = lifecycle.ApprovedTask(issue, run_id, digest, base)
        if state == 'running':
            try:
                observe_finish(api, conn, task=task, now=now)
            except TransportBlocked as exc:
                if str(exc) == 'WORKFLOW_NOT_COMPLETED':
                    ready = False
                    continue
                raise
        lifecycle.reconcile(conn, task=task, now=now, reader=reader)
    return ready


def serve(api, connect, *, trusted_sha, stop, logger=print,
          clock=lambda: datetime.now(timezone.utc)):
    """Explicit polling process; SIGTERM never releases a reservation."""
    last = None
    while not stop.is_set():
        delay = 5
        try:
            with connect() as conn:
                if refresh_runs(api, conn):
                    if stop.is_set():
                        break
                    count = poll_once(api, conn, trusted_sha=trusted_sha, accepting=lambda: not stop.is_set())
                    message = 'READY: private controller polling' if not count else 'PASS: reservation committed'
                else:
                    message = 'WAIT: active execution retains reservation'
        except CostGateBlocked as exc:
            code = "COSTS_RATE_LIMITED" if str(exc) == "COSTS_RATE_LIMITED" else "COSTS_UNAVAILABLE"
            message, delay = "BLOCKED: " + code, 60
            if code == 'COSTS_RATE_LIMITED':
                retry = getattr(exc, 'retry_after_seconds', None)
                delay = retry if type(retry) is int and 900 <= retry <= 86400 else 900
                # Report the effective validated wait, never raw headers/errors.
                # Every 429 needs a new deadline even if the fixed code repeats.
                resume_at = lifecycle.utc(clock()) + timedelta(seconds=delay)
                if resume_at.microsecond:
                    resume_at = (resume_at + timedelta(seconds=1)).replace(microsecond=0)
                logger('COSTS_BACKOFF: ' + json.dumps({
                    'code': 'COSTS_RATE_LIMITED',
                    'effective_retry_after_seconds': delay,
                    'not_before_utc': resume_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'delay_source': 'validated_metadata' if delay == retry and
                        type(retry) is int else 'fallback',
                }, sort_keys=True))
        except lifecycle.ExecutionBlocked as exc:
            if str(exc) == 'COSTS_NOT_YET_COVERING_EXECUTION':
                message, delay = 'WAIT: COSTS_NOT_YET_COVERING_EXECUTION', 900
            else:
                message, delay = 'BLOCKED: PRIVATE_CONTROLLER_CHECK_FAILED', 60
        except (TransportBlocked, policy.Blocked):
            # Leave holds untouched. API/DB/Costs errors cannot grant a receipt.
            message, delay = 'BLOCKED: PRIVATE_CONTROLLER_CHECK_FAILED', 60
        except Exception:
            message, delay = 'BLOCKED: PRIVATE_CONTROLLER_FAILURE', 60
        if message != last:
            logger(message)
            last = message
        stop.wait(delay)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    opted_in(os.environ)
    if argv == ['request']:
        request_file()
    elif argv == ['wait']:
        payload = json.loads(Path('budget-request/request.json').read_text())
        wait_receipt(policy.API(), payload)
    elif argv in (['--poll-once'], ['--serve']):
        token = os.environ.get('FOCUS_BUDGET_GITHUB_TOKEN', '')
        pinned = os.environ.get('FOCUS_BUDGET_TRUSTED_SHA', '')
        if not token or not policy.SHA.fullmatch(pinned):
            raise TransportBlocked('PRIVATE_CONTROLLER_AUTH_REQUIRED')
        from render_private_bootstrap import validate_private_url
        url = os.environ.get('CODEX_BUDGET_DATABASE_URL', '')
        if validate_private_url(url):
            raise TransportBlocked('PRIVATE_DATABASE_REQUIRED')
        import psycopg
        api = policy.API(token=token)
        if api.call('GET', '/user').get('login') != RECEIPT_LOGIN:
            raise TransportBlocked('PRIVATE_CONTROLLER_IDENTITY_REQUIRED')
        connect = lambda: psycopg.connect(url, connect_timeout=10)
        # Does not auto-provision schema or run a model.
        if argv == ['--serve']:
            stop = threading.Event()
            signal.signal(signal.SIGTERM, lambda *args: stop.set())
            signal.signal(signal.SIGINT, lambda *args: stop.set())
            # Read-only diagnostic at process startup, separate from polling semantics.
            try:
                from .budget_diagnostic import emit_snapshot
            except ImportError:
                from budget_diagnostic import emit_snapshot
            if not stop.is_set():
                try:
                    with connect() as diagnostic_conn:
                        emit_snapshot(diagnostic_conn, lambda message: print(message, flush=True))
                except Exception:
                    print('BUDGET_DIAGNOSTIC: UNAVAILABLE', flush=True)
            try:
                from .costs_cooldown import wait_for_costs_window
            except ImportError:
                from costs_cooldown import wait_for_costs_window
            logger = lambda message: print(message, flush=True)
            if wait_for_costs_window(os.environ, stop, logger):
                try:
                    from .costs_recovery import observe_recovery
                except ImportError:
                    from costs_recovery import observe_recovery
                if observe_recovery(os.environ, stop, logger):
                    serve(api, connect, trusted_sha=pinned, stop=stop, logger=logger)
        else:
            with connect() as conn:
                count = poll_once(api, conn, trusted_sha=pinned) if refresh_runs(api, conn) else 0
            print('PASS: private requests admitted=' + str(count))
    else:
        raise TransportBlocked('EXPLICIT_TRANSPORT_COMMAND_REQUIRED')


if __name__ == '__main__':
    try:
        main()
    except (TransportBlocked, lifecycle.ExecutionBlocked, policy.Blocked) as exc:
        print('BLOCKED: '+str(exc), file=sys.stderr)
        raise SystemExit(1) from None
    except Exception:
        print('BLOCKED: PRIVATE_TRANSPORT_FAILURE', file=sys.stderr)
        raise SystemExit(1) from None
