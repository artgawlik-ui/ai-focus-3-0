"""Explicit isolated-DB diagnostic. Temporary tables only, no model calls.

The live read proves admission can consume authenticated project costs. Synthetic
future observations test reconciliation separately; never label those live costs.
No durable schema change or production application operation is performed.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import sys

from durable_reservations import SCHEMA as RESERVATIONS_SCHEMA
from live_cost_gate import check_live_costs
from private_execution import ApprovedTask, ExecutionBlocked, SCHEMA, admit, finish, reconcile
from render_private_bootstrap import validate_private_url


def expect_block(code, operation):
    try:
        operation()
    except ExecutionBlocked as exc:
        if str(exc) == code:
            return
        raise
    raise RuntimeError('EXPECTED_BLOCK_MISSING')


def main(argv=None):
    if argv != ['--temporary-tables-only']:
        raise RuntimeError('EXPLICIT_TEMPORARY_DIAGNOSTIC_REQUIRED')
    url = os.environ.get('CODEX_BUDGET_DATABASE_URL', '')
    if validate_private_url(url):
        raise RuntimeError('PRIVATE_DATABASE_REQUIRED')
    import psycopg
    now = datetime.now(timezone.utc)
    observation = check_live_costs(now=now)
    live_reader = lambda **kw: (observation.spend_usd, observation.covered_until)
    task = ApprovedTask(990041, '990041:1', 'a'*64, 'b'*40)
    second = ApprovedTask(990042, '990042:1', 'c'*64, 'b'*40)
    with psycopg.connect(url, connect_timeout=10) as conn:
        # Both tables shadow the durable schema in this connection. Explicitly
        # verify namespaces before executing any inserts/updates.
        with conn.transaction():
            conn.execute(RESERVATIONS_SCHEMA.replace('CREATE TABLE IF NOT EXISTS', 'CREATE TEMP TABLE'))
            conn.execute(SCHEMA.replace('CREATE TABLE IF NOT EXISTS', 'CREATE TEMP TABLE'))
            names = conn.execute("SELECT c.relname,n.nspname LIKE 'pg_temp_%' "
                                 'FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace '
                                 "WHERE c.oid IN ('codex_budget_reservations'::regclass,"
                                 "'codex_execution_runs'::regclass)").fetchall()
            if len(names) != 2 or not all(row[1] for row in names):
                raise RuntimeError('TEMP_TABLE_ISOLATION_REQUIRED')
        admit(conn, task=task, authorize=lambda t: t == task, now=now, reader=live_reader)
        print('PASS: real Costs API observation admitted into temporary PostgreSQL lifecycle')
        expect_block('UNRECONCILED_EXECUTION', lambda: admit(
            conn, task=second, authorize=lambda t: t == second, now=now, reader=live_reader))
        finish(conn, task=task, outcome='unknown', now=now)
        expect_block('COSTS_NOT_YET_COVERING_EXECUTION', lambda: reconcile(
            conn, task=task, now=now, reader=live_reader))
        expect_block('UNRECONCILED_EXECUTION', lambda: admit(
            conn, task=second, authorize=lambda t: t == second, now=now, reader=live_reader))
        print('PASS: unfinished and finished-but-unreported runs retain hold')
        # This branch uses an explicitly synthetic later observation. It cannot
        # release a durable reservation because both tables are temporary.
        synthetic_now = now + timedelta(minutes=1)
        synthetic_reader = lambda **kw: (Decimal('.10'), synthetic_now)
        reconcile(conn, task=task, now=synthetic_now, reader=synthetic_reader)
        expect_block('EXECUTION_ADMISSION_UNAVAILABLE', lambda: admit(
            conn, task=task, authorize=lambda t: True, now=synthetic_now, reader=synthetic_reader))
        admit(conn, task=second, authorize=lambda t: True, now=synthetic_now, reader=synthetic_reader)
        finish(conn, task=second, outcome='cancelled', now=synthetic_now)
        reconcile(conn, task=second, now=synthetic_now, reader=synthetic_reader)
        with conn.transaction():
            held = conn.execute('SELECT SUM(amount_usd) FROM codex_budget_reservations').fetchone()[0]
            if held != Decimal('4'):
                raise RuntimeError('SETTLED_ALLOWANCE_WAS_RECYCLED')
        print('PASS: synthetic reconciliation retains 4 USD allowances; duplicate run blocked')
        high_reader = lambda **kw: (Decimal('3.99'), synthetic_now)
        third = ApprovedTask(990043, '990043:1', 'd'*64, 'b'*40)
        admit(conn, task=third, authorize=lambda t: True, now=synthetic_now, reader=synthetic_reader)
        finish(conn, task=third, outcome='failure', now=synthetic_now)
        reconcile(conn, task=third, now=synthetic_now, reader=synthetic_reader)
        fourth = ApprovedTask(990044, '990044:1', 'e'*64, 'b'*40)
        expect_block('MONTHLY_BUDGET', lambda: admit(
            conn, task=fourth, authorize=lambda t: True, now=synthetic_now, reader=high_reader))
        print('PASS: settled allowances plus provider spend block overspend')
    print('PASS: connection closed, temporary tables removed; durable rows unchanged; paid calls=0')


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception:
        print('BLOCKED: PRIVATE_LIFECYCLE_DIAGNOSTIC_FAILED', file=sys.stderr)
        raise SystemExit(1) from None
