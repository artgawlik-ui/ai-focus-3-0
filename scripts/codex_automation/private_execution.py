"""Private PostgreSQL execution lifecycle; no executor, transport or model calls.

Only the trusted controller may supply the authorization callback. A finished or
crashed run keeps its hold until authenticated reporting covers its finish time.
Even after reconciliation its full allowance remains charged for the month; the
project-wide Costs API cannot establish the exact cost of an individual run.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import re

try:
    from .durable_reservations import CAP, RESERVE
    from .live_cost_gate import check_live_costs
except ImportError:
    from durable_reservations import CAP, RESERVE
    from live_cost_gate import check_live_costs

SCHEMA = """
CREATE TABLE IF NOT EXISTS codex_execution_runs (
    run_id text PRIMARY KEY,
    reservation_id text NOT NULL UNIQUE REFERENCES codex_budget_reservations(reservation_id),
    issue_number integer NOT NULL CHECK (issue_number > 0),
    task_digest text NOT NULL,
    base_sha text NOT NULL,
    state text NOT NULL CHECK (state IN ('running','awaiting_costs','reconciled')),
    started_at timestamptz NOT NULL,
    finished_at timestamptz,
    outcome text CHECK (outcome IN ('success','failure','cancelled','unknown')),
    observed_spend_usd numeric,
    covered_until timestamptz,
    CHECK ((state='running' AND finished_at IS NULL AND outcome IS NULL) OR
           (state<>'running' AND finished_at IS NOT NULL AND outcome IS NOT NULL)),
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS codex_one_unreconciled_execution
ON codex_execution_runs ((true)) WHERE state <> 'reconciled';
"""


class ExecutionBlocked(RuntimeError):
    """Fixed safe codes only."""


@dataclass(frozen=True)
class ApprovedTask:
    issue: int
    run_id: str
    digest: str
    base: str

    def validate(self):
        if (type(self.issue) is not int or self.issue < 1 or
            not isinstance(self.run_id, str) or
            not re.fullmatch(r'[1-9][0-9]{0,19}:1', self.run_id) or
            not isinstance(self.digest, str) or not re.fullmatch(r'[a-f0-9]{64}', self.digest) or
            not isinstance(self.base, str) or not re.fullmatch(r'[a-f0-9]{40}', self.base)):
            raise ExecutionBlocked('INVALID_APPROVED_TASK')


def utc(now):
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ExecutionBlocked('UTC_CLOCK_REQUIRED')
    return now.astimezone(timezone.utc)


def lock(cur):
    # Global, including month rollover; never bypass an unresolved previous run.
    cur.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', ('focus-codex-execution',))


def admit(conn, *, task, authorize, env=None, now=None, reader=None):
    task.validate()
    now = utc(now)
    try:
        authorized = authorize(task)
    except Exception:
        raise ExecutionBlocked('TASK_AUTHORIZATION_REQUIRED') from None
    if authorized is not True:
        raise ExecutionBlocked('TASK_AUTHORIZATION_REQUIRED')
    observation = check_live_costs(env=env, now=now, reader=reader)
    reservation = 'github-run-' + task.run_id
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                lock(cur)
                cur.execute("SELECT 1 FROM codex_budget_reservations WHERE state='reserved' LIMIT 1")
                if cur.fetchone() is not None:
                    raise ExecutionBlocked('UNRECONCILED_EXECUTION')
                # Settled allowances are deliberately retained: no budget is
                # recycled from aggregate provider totals or a local success.
                cur.execute('SELECT COALESCE(SUM(amount_usd),0) FROM codex_budget_reservations '
                            "WHERE month=%s AND state IN ('reserved','settled')",
                            (observation.billing_month,))
                held = Decimal(str(cur.fetchone()[0]))
                if observation.spend_usd + held + RESERVE > CAP:
                    raise ExecutionBlocked('MONTHLY_BUDGET')
                cur.execute('INSERT INTO codex_budget_reservations '
                            '(reservation_id,month,issue_number,amount_usd,state) '
                            "VALUES (%s,%s,%s,%s,'reserved')",
                            (reservation, observation.billing_month, task.issue, RESERVE))
                cur.execute('INSERT INTO codex_execution_runs '
                            '(run_id,reservation_id,issue_number,task_digest,base_sha,state,started_at,'
                            'observed_spend_usd,covered_until) '
                            "VALUES (%s,%s,%s,%s,%s,'running',%s,%s,%s)",
                            (task.run_id, reservation, task.issue, task.digest, task.base, now,
                             observation.spend_usd, observation.covered_until))
    except ExecutionBlocked:
        raise
    except Exception:
        raise ExecutionBlocked('EXECUTION_ADMISSION_UNAVAILABLE') from None
    return observation


def finish(conn, *, task, outcome, now=None):
    task.validate()
    now = utc(now)
    if outcome not in {'success','failure','cancelled','unknown'}:
        raise ExecutionBlocked('INVALID_EXECUTION_OUTCOME')
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                lock(cur)
                cur.execute("UPDATE codex_execution_runs SET state='awaiting_costs', "
                            'finished_at=%s,outcome=%s WHERE run_id=%s AND issue_number=%s AND task_digest=%s '
                            "AND base_sha=%s AND state='running' AND started_at <= %s",
                            (now, outcome, task.run_id, task.issue, task.digest, task.base, now))
                if cur.rowcount != 1:
                    raise ExecutionBlocked('RUN_MISMATCH_OR_ALREADY_FINISHED')
    except ExecutionBlocked:
        raise
    except Exception:
        raise ExecutionBlocked('EXECUTION_FINISH_UNAVAILABLE') from None


def reconcile(conn, *, task, env=None, now=None, reader=None):
    task.validate()
    observation = check_live_costs(env=env, now=utc(now), reader=reader)
    try:
        with conn.transaction():
            with conn.cursor() as cur:
                lock(cur)
                cur.execute('SELECT reservation_id,finished_at,state FROM codex_execution_runs '
                            'WHERE run_id=%s AND issue_number=%s AND task_digest=%s AND base_sha=%s FOR UPDATE',
                            (task.run_id, task.issue, task.digest, task.base))
                row = cur.fetchone()
                if row is None or row[2] != 'awaiting_costs':
                    raise ExecutionBlocked('FINISHED_RUN_REQUIRED')
                if row[1] is None or observation.covered_until < row[1]:
                    raise ExecutionBlocked('COSTS_NOT_YET_COVERING_EXECUTION')
                cur.execute("UPDATE codex_budget_reservations SET state='settled' "
                            "WHERE reservation_id=%s AND state='reserved'", (row[0],))
                if cur.rowcount != 1:
                    raise ExecutionBlocked('RESERVATION_MISMATCH')
                cur.execute("UPDATE codex_execution_runs SET state='reconciled', "
                            'observed_spend_usd=%s,covered_until=%s WHERE run_id=%s',
                            (observation.spend_usd, observation.covered_until, task.run_id))
    except ExecutionBlocked:
        raise
    except Exception:
        raise ExecutionBlocked('RECONCILIATION_UNAVAILABLE') from None
    return observation
