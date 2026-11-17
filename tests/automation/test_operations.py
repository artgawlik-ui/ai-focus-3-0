import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from scripts.codex_automation.operations import checkpoint, ci_state, plan, validate_queue

NOW = datetime(2026, 11, 17, 18, 0, tzinfo=timezone.utc)
SHA = 'a' * 40
QUEUE = json.loads(Path('scripts/codex_automation/operations_queue.json').read_text())


def facts():
    return {'repository': QUEUE['repository'], 'main_sha': SHA,
            'observed_at': NOW.isoformat(), 'inventory_complete': True,
            'active_executor_runs': [], 'leases': [], 'task_states': {}}


class OperationsTests(unittest.TestCase):
    def test_blocked_paid_path_does_not_starve_verified_free_work(self):
        state = facts()
        state['task_states']['technical-access'] = {
            'status': 'READY', 'verified': True, 'evidence': ['reviewed-existing-worker']}
        result = plan(QUEUE, state, now=NOW)
        self.assertEqual(result['next_task'], 'technical-access')
        self.assertFalse(result['paid_authorized'])
        self.assertEqual(result['tasks'][2]['reason'], 'DEPENDENCY')

    def test_unverified_ready_and_done_cannot_satisfy_dependencies(self):
        state = facts()
        state['task_states']['dependency-review'] = {'status': 'DONE', 'verified': True}
        state['task_states']['technical-access'] = {'status': 'READY', 'verified': False, 'evidence': ['x']}
        result = plan(QUEUE, state, now=NOW)
        self.assertIsNone(result['next_task'])
        self.assertEqual(result['tasks'][1]['reason'], 'DEPENDENCY')

    def test_even_verified_done_dependencies_never_authorize_paid_or_private_calls(self):
        state = facts()
        for task in QUEUE['tasks']:
            state['task_states'][task['id']] = {'status': 'DONE', 'verified': True, 'evidence': ['proof']}
        for name in ('incident65', 'transport', 'executor'):
            partial = copy.deepcopy(state)
            partial['task_states'][name]['status'] = 'READY'
            result = plan(QUEUE, partial, now=NOW)
            self.assertFalse(result['paid_authorized'])
            self.assertEqual(next(t for t in result['tasks'] if t['id'] == name)['status'], 'BLOCKED')

    def test_restart_claim_blocks_until_expiry_without_replaying_uncertain_task(self):
        state = facts()
        state['task_states']['technical-access'] = {'status': 'READY', 'verified': True, 'evidence': ['proof']}
        state['leases'] = [{'expires_at': '2026-11-17T18:01:00Z'}]
        self.assertEqual(plan(QUEUE, state, now=NOW)['reason'], 'ACTIVE_WORK')
        state['leases'][0]['expires_at'] = '2026-11-17T17:59:00Z'
        state['task_states']['technical-access']['uncertain_execution'] = True
        self.assertIsNone(plan(QUEUE, state, now=NOW)['next_task'])

    def test_waiting_environment_run_blocks_duplicate_executor(self):
        state = facts()
        state['active_executor_runs'] = [{'status': 'waiting', 'id': 123}]
        self.assertEqual(plan(QUEUE, state, now=NOW)['reason'], 'ACTIVE_WORK')

    def test_stale_future_partial_and_missing_inventory_fail_closed(self):
        for date in ('2026-11-17T17:49:00Z', '2026-11-17T18:01:00Z'):
            state = facts()
            state['observed_at'] = date
            self.assertEqual(plan(QUEUE, state, now=NOW)['reason'], 'STALE_SNAPSHOT')
        state = facts()
        state['inventory_complete'] = False
        self.assertEqual(plan(QUEUE, state, now=NOW)['reason'], 'INCOMPLETE_INVENTORY')
        del state['active_executor_runs']
        state['inventory_complete'] = True
        with self.assertRaises(ValueError):
            plan(QUEUE, state, now=NOW)

    def test_attempt_budget_prevents_infinite_free_retries(self):
        state = facts()
        state['task_states']['technical-access'] = {
            'status': 'READY', 'verified': True, 'evidence': ['proof'], 'attempts': 2}
        result = plan(QUEUE, state, now=NOW)
        self.assertEqual(result['tasks'][4]['reason'], 'ATTEMPT_LIMIT_REVIEW_REQUIRED')

    def test_two_synthetic_completions_move_to_next_task_without_owner_prompt(self):
        state = facts()
        for name in ('technical-access', 'review-release', 'recovery'):
            state['task_states'][name] = {'status': 'READY', 'verified': True, 'evidence': ['synthetic']}
        self.assertEqual(plan(QUEUE, state, now=NOW)['next_task'], 'technical-access')
        state['task_states']['technical-access']['status'] = 'DONE'
        self.assertEqual(plan(QUEUE, state, now=NOW)['next_task'], 'review-release')
        state['task_states']['review-release']['status'] = 'DONE'
        self.assertEqual(plan(QUEUE, state, now=NOW)['next_task'], 'recovery')

    def test_same_semantic_report_suppressed_after_restart_but_changed_blocker_notifies(self):
        state = facts()
        first = checkpoint(plan(QUEUE, state, now=NOW))
        state['observed_at'] = '2026-11-17T17:59:59Z'
        second = checkpoint(plan(QUEUE, state, now=NOW), first['fingerprint'])
        self.assertFalse(second['notify'])
        state['active_executor_runs'] = [{'id': 1}]
        self.assertTrue(checkpoint(plan(QUEUE, state, now=NOW), first['fingerprint'])['notify'])

    def test_exact_sha_ci_latest_attempt_and_all_required_workflows(self):
        checks = [{'name': name, 'head_sha': SHA, 'id': 1, 'run_attempt': 1,
                   'status': 'completed', 'conclusion': 'success'}
                  for name in ('Verify Focus 3', 'Codex automation policy tests')]
        self.assertEqual(ci_state(checks, SHA), 'PASS')
        self.assertEqual(ci_state(checks, 'b' * 40), 'UNKNOWN')
        checks.append(dict(checks[0], run_attempt=2, status='in_progress', conclusion=None))
        self.assertEqual(ci_state(checks, SHA), 'WAIT')
        checks[-1].update(status='completed', conclusion='failure')
        self.assertEqual(ci_state(checks, SHA), 'FAIL')

    def test_queue_rejects_cycles_and_missing_dependency(self):
        for dep in ('dependency-review', 'not-a-task'):
            queue = copy.deepcopy(QUEUE)
            queue['tasks'][0]['depends_on'] = [dep]
            with self.assertRaises(ValueError):
                validate_queue(queue)

    def test_wrong_repository_and_negative_attempts_rejected(self):
        state = facts()
        state['repository'] = 'other/repo'
        with self.assertRaises(ValueError):
            plan(QUEUE, state, now=NOW)
        state = facts()
        state['task_states']['technical-access'] = {'attempts': -1}
        with self.assertRaises(ValueError):
            plan(QUEUE, state, now=NOW)
