"""Safety contracts for private execution; no paid calls or database credentials."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock, Mock

from scripts.codex_automation import private_execution as p
from scripts.codex_automation.live_cost_gate import CostGateBlocked

NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
ENV = {'OPENAI_COSTS_ADMIN_KEY': 'synthetic', 'OPENAI_PROJECT_ID': 'proj_test'}
TASK = p.ApprovedTask(40, '123:1', 'a'*64, 'b'*40)


def database(rows):
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.side_effect = rows
    cur.rowcount = 1
    return conn, cur


class PrivateExecutionTests(TestCase):
    def test_no_authorization_no_costs_no_database(self):
        for authorize in (lambda task: False, lambda task: 'true', Mock(side_effect=Exception('secret'))):
            conn, reader = Mock(), Mock()
            with self.assertRaisesRegex(p.ExecutionBlocked, '^TASK_AUTHORIZATION_REQUIRED$'):
                p.admit(conn, task=TASK, authorize=authorize, reader=reader, now=NOW)
            reader.assert_not_called()
            conn.cursor.assert_not_called()

    def test_run_identity_rejects_reruns_and_injections(self):
        for run_id in ('123:2', '123\n:1', '0:1', '../../x', 123, '123:1;sh'):
            with self.subTest(run=run_id), self.assertRaisesRegex(p.ExecutionBlocked, 'INVALID_APPROVED_TASK'):
                p.ApprovedTask(40, run_id, 'a'*64, 'b'*40).validate()

    def test_absent_costs_never_open_transaction(self):
        conn = Mock()
        with self.assertRaises(CostGateBlocked):
            p.admit(conn, task=TASK, authorize=lambda task: True, env={}, now=NOW)
        conn.cursor.assert_not_called()

    def test_unresolved_previous_month_blocks_even_with_low_spend(self):
        conn, cur = database([(1,)])
        with self.assertRaisesRegex(p.ExecutionBlocked, 'UNRECONCILED_EXECUTION'):
            p.admit(conn, task=TASK, authorize=lambda task: True, env=ENV, now=NOW,
                    reader=lambda **kw: (Decimal('.03'), NOW))
        self.assertFalse(any('INSERT' in c.args[0] for c in cur.execute.call_args_list))

    def test_settled_allowances_are_not_recycled(self):
        conn, cur = database([None, (Decimal('6'),)])
        with self.assertRaisesRegex(p.ExecutionBlocked, 'MONTHLY_BUDGET'):
            p.admit(conn, task=TASK, authorize=lambda task: True, env=ENV, now=NOW,
                    reader=lambda **kw: (Decimal('.03'), NOW))
        self.assertIn("'settled'", cur.execute.call_args.args[0])

    def test_admission_writes_run_and_reservation_in_same_transaction(self):
        conn, cur = database([None, (0,)])
        p.admit(conn, task=TASK, authorize=lambda task: True, env=ENV, now=NOW,
                reader=lambda **kw: (Decimal('.03'), NOW))
        self.assertEqual(conn.transaction.call_count, 1)
        sql = [call.args[0] for call in cur.execute.call_args_list]
        self.assertEqual(sum('INSERT INTO' in q for q in sql), 2)
        self.assertIn('pg_advisory_xact_lock', sql[0])

    def test_success_failure_cancellation_all_keep_hold(self):
        for outcome in ('success', 'failure', 'cancelled', 'unknown'):
            conn, cur = database([])
            p.finish(conn, task=TASK, outcome=outcome, now=NOW)
            sql = ' '.join(c.args[0] for c in cur.execute.call_args_list)
            self.assertIn('awaiting_costs', sql)
            self.assertNotIn('UPDATE codex_budget_reservations', sql)

    def test_finish_mismatch_fails_without_releasing(self):
        conn, cur = database([])
        cur.rowcount = 0
        with self.assertRaisesRegex(p.ExecutionBlocked, 'RUN_MISMATCH_OR_ALREADY_FINISHED'):
            p.finish(conn, task=TASK, outcome='success', now=NOW)

    def test_costs_before_finish_cannot_reconcile(self):
        conn, cur = database([('github-run-123:1', NOW, 'awaiting_costs')])
        with self.assertRaisesRegex(p.ExecutionBlocked, 'COSTS_NOT_YET_COVERING_EXECUTION'):
            p.reconcile(conn, task=TASK, env=ENV, now=NOW,
                        reader=lambda **kw: (Decimal('.03'), NOW-timedelta(hours=1)))
        self.assertFalse(any(c.args[0].lstrip().startswith('UPDATE ') for c in cur.execute.call_args_list))

    def test_reconciliation_requires_finished_exact_run(self):
        for row in (None, ('r', NOW, 'running'), ('r', NOW, 'reconciled')):
            conn, _ = database([row])
            with self.assertRaisesRegex(p.ExecutionBlocked, 'FINISHED_RUN_REQUIRED'):
                p.reconcile(conn, task=TASK, env=ENV, now=NOW,
                            reader=lambda **kw: (Decimal('.03'), NOW))

    def test_covered_finished_run_settled_and_retained(self):
        conn, cur = database([('github-run-123:1', NOW, 'awaiting_costs')])
        p.reconcile(conn, task=TASK, env=ENV, now=NOW,
                    reader=lambda **kw: (Decimal('.03'), NOW))
        sql = ' '.join(c.args[0] for c in cur.execute.call_args_list)
        self.assertIn("state='settled'", sql)
        self.assertNotIn('DELETE', sql)

    def test_database_failure_is_sanitized(self):
        conn = MagicMock()
        conn.cursor.side_effect = RuntimeError('synthetic secret')
        with self.assertRaisesRegex(p.ExecutionBlocked, '^EXECUTION_ADMISSION_UNAVAILABLE$'):
            p.admit(conn, task=TASK, authorize=lambda task: True, env=ENV, now=NOW,
                    reader=lambda **kw: (Decimal('.03'), NOW))


class AuthorizationExpiryTests(TestCase):
    def test_authorization_expiring_after_cost_read_never_inserts(self):
        for second in (False,'true',RuntimeError('SYNTHETIC_SECRET')):
            conn,cur=database([])
            authorize=Mock(side_effect=[True,second])
            reader=Mock(return_value=(Decimal('.03'),NOW))
            with self.subTest(second=type(second).__name__), self.assertRaisesRegex(p.ExecutionBlocked,'^TASK_AUTHORIZATION_REQUIRED$'):
                p.admit(conn,task=TASK,authorize=authorize,env=ENV,now=NOW,reader=reader)
            reader.assert_called_once()
            self.assertEqual(authorize.call_count,2)
            self.assertIn('pg_advisory_xact_lock',cur.execute.call_args_list[0].args[0])
            self.assertFalse(any('INSERT' in c.args[0] for c in cur.execute.call_args_list))
