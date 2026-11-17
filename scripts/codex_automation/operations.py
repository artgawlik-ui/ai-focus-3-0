"""Offline operational planner for the existing coordinator, NOT paid admission.

Inputs are fresh, independently collected GitHub/Render facts. No network,
credentials, model, merge, deploy, database write or scheduling side effects.
Durable queue lives in Git; checkpoint/result/lease live in issue #39.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

REPO = 'artgawlik-ui/ai-focus-3-0'
SHA = re.compile(r'[a-f0-9]{40}\Z')
ACTIVE = {'queued', 'requested', 'waiting', 'pending', 'in_progress'}
MODES = {'offline', 'private-diagnostic', 'no-model', 'paid'}
REQUIRED_CHECKS = {'Verify Focus 3', 'Codex automation policy tests'}


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    return result.astimezone(timezone.utc)


def validate_queue(queue):
    if queue['version'] != 1 or queue['repository'] != REPO:
        raise ValueError('QUEUE_SCOPE')
    tasks = queue['tasks']
    ids = [t['id'] for t in tasks]
    if len(ids) != len(set(ids)) or not tasks:
        raise ValueError('QUEUE_IDS')
    by_id = {t['id']: t for t in tasks}
    for task in tasks:
        if (task['mode'] not in MODES or type(task['issue']) is not int or
                task['issue'] <= 0 or not task['scope'] or not task['acceptance'] or
                any(dep not in by_id for dep in task['depends_on'])):
            raise ValueError('QUEUE_TASK')
    def visit(key, path):
        if key in path:
            raise ValueError('QUEUE_CYCLE')
        for dep in by_id[key]['depends_on']:
            visit(dep, path | {key})
    for key in ids:
        visit(key, set())


def ci_state(checks, sha):
    """Latest attempt per workflow on EXACT SHA; old green runs cannot win."""
    relevant = [c for c in checks if c.get('head_sha') == sha and
                c.get('name') in REQUIRED_CHECKS]
    latest = {}
    for check in relevant:
        order = (check['id'], check.get('run_attempt', 1))
        old = latest.get(check['name'])
        if old is None or order > (old['id'], old.get('run_attempt', 1)):
            latest[check['name']] = check
    if set(latest) != REQUIRED_CHECKS:
        return 'UNKNOWN'
    if any(c['status'] != 'completed' for c in latest.values()):
        return 'WAIT'
    return 'PASS' if all(c.get('conclusion') == 'success' for c in latest.values()) else 'FAIL'


def plan(queue, facts, *, now):
    validate_queue(queue)
    if facts['repository'] != REPO or not SHA.fullmatch(facts['main_sha']):
        raise ValueError('SNAPSHOT_SCOPE')
    age = (now - utc(facts['observed_at'])).total_seconds()
    result = {'status': 'BLOCKED', 'reason': 'STALE_SNAPSHOT', 'next_task': None,
              'main_sha': facts['main_sha'], 'tasks': [], 'paid_authorized': False}
    if not 0 <= age <= 600:
        return result
    # Inventory completeness is explicit; an empty partial page proves nothing.
    if facts.get('inventory_complete') is not True:
        result['reason'] = 'INCOMPLETE_INVENTORY'
        return result
    if not all(isinstance(facts.get(key), list) for key in ('active_executor_runs', 'leases')):
        raise ValueError('ACTIVE_INVENTORY_REQUIRED')
    if facts['active_executor_runs'] or any(
            utc(lease['expires_at']) > now for lease in facts['leases']):
        result.update(status='WAIT', reason='ACTIVE_WORK')
        return result
    states = facts['task_states']
    if not isinstance(states, dict):
        raise ValueError('TASK_STATES_REQUIRED')
    for value in states.values():
        attempts = value.get('attempts', 0)
        if type(attempts) is not int or attempts < 0:
            raise ValueError('INVALID_ATTEMPTS')
    done = {key for key, value in states.items()
            if value.get('status') == 'DONE' and value.get('verified') is True
            and value.get('evidence')}
    for task in queue['tasks']:
        state = states.get(task['id'], {})
        status, reason = 'BLOCKED', 'UNASSESSED'
        if task['id'] in done:
            status, reason = 'DONE', 'VERIFIED_COMPLETION'
        elif any(dep not in done for dep in task['depends_on']):
            reason = 'DEPENDENCY'
        elif task['mode'] != 'offline':
            # This planner can NEVER authorize CostsGET, receipt, paid API or deployment.
            reason = 'EXTERNAL_GATE_REQUIRES_VERIFICATION'
        elif state.get('uncertain_execution') is True:
            reason = 'UNCERTAIN_EXECUTION_NO_REPLAY'
        elif state.get('attempts', 0) >= queue['max_attempts']:
            reason = 'ATTEMPT_LIMIT_REVIEW_REQUIRED'
        elif state.get('status') == 'READY' and state.get('verified') is True and state.get('evidence'):
            status, reason = 'READY', 'OFFLINE_SCOPE_VERIFIED'
        result['tasks'].append({'id': task['id'], 'issue': task['issue'],
                                'status': status, 'reason': reason})
        if status == 'READY' and result['next_task'] is None:
            result.update(status='READY', reason=reason, next_task=task['id'])
    if all(t['status'] == 'DONE' for t in result['tasks']):
        result.update(status='DONE', reason='QUEUE_COMPLETE')
    elif result['next_task'] is None:
        result['reason'] = 'NO_VERIFIED_OFFLINE_WORK'
    return result


def checkpoint(result, previous=None):
    """Persist this SAFE fixed-schema object in #39, under the coordinator lease.

    Caller supplies previous fingerprint from the latest durable checkpoint.
    No task text, secrets, raw API payloads or observed_at enter the fingerprint.
    """
    raw = json.dumps(result, sort_keys=True, separators=(',', ':'))
    fingerprint = hashlib.sha256(raw.encode()).hexdigest()
    return {'schema': 1, 'fingerprint': fingerprint,
            'notify': fingerprint != previous, 'result': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--previous-fingerprint')
    args = parser.parse_args()
    try:
        queue = json.loads(Path(__file__).with_name('operations_queue.json').read_text())
        facts = json.loads(args.snapshot.read_text())
        result = plan(queue, facts, now=datetime.now(timezone.utc))
        print(json.dumps(checkpoint(result, args.previous_fingerprint), sort_keys=True))
    except (KeyError, ValueError, TypeError, OSError):
        print('{"status":"BLOCKED","reason":"INVALID_OPERATIONS_INPUT"}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
