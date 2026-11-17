"""Read-only snapshot of the existing #50 hold. Never calls Costs or reconcile."""
from datetime import datetime
from decimal import Decimal
import json

RUN = '43909025185:1'

def snapshot(conn):
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            cur.execute('SELECT covered_until,finished_at FROM codex_execution_runs '
                        'WHERE run_id=%s AND issue_number=50', (RUN,))
            rows = cur.fetchall()
            if len(rows) != 1:
                return {'status':'UNVERIFIED_RUN'}
            covered, finished = rows[0]
            if (not isinstance(covered, datetime) or not isinstance(finished, datetime)
                    or covered.utcoffset() is None or finished.utcoffset() is None
                    or covered < finished):
                return {'status':'COSTS_NOT_COVERING_FINISH'}
            # Only after authenticated persisted Costs coverage: inspect the hold.
            cur.execute('SELECT e.state,r.state,r.amount_usd,r.month,e.observed_spend_usd '
                        'FROM codex_execution_runs e JOIN codex_budget_reservations r '
                        'ON r.reservation_id=e.reservation_id '
                        'WHERE e.run_id=%s AND e.issue_number=50 AND r.issue_number=50', (RUN,))
            matches = cur.fetchall()
            if len(matches) != 1:
                return {'status':'UNVERIFIED_RESERVATION'}
            execution, reservation, amount, month, spend = matches[0]
            if (execution not in {'running','awaiting_costs','reconciled'}
                    or reservation not in {'reserved','settled','blocked'}
                    or amount != Decimal('2') or month != '2026-11'
                    or not isinstance(spend, Decimal) or not spend.is_finite() or spend < 0):
                return {'status':'INVALID_SNAPSHOT'}
            cur.execute('SELECT COUNT(*) FROM codex_budget_reservations WHERE issue_number=50')
            count = cur.fetchone()[0]
            cur.execute('SELECT COALESCE(SUM(amount_usd),0) FROM codex_budget_reservations '
                        "WHERE month=%s AND state IN ('reserved','settled')", (month,))
            held = Decimal(str(cur.fetchone()[0]))
            if not held.is_finite() or held < 0:
                return {'status':'INVALID_SNAPSHOT'}
            return {
                'status': 'AUTOMATICALLY_RECONCILED' if
                    execution == 'reconciled' and reservation == 'settled' and count == 1
                    else 'UNVERIFIED_SETTLEMENT',
                'costs_cover_finish': True,
                'covered_until': covered.isoformat(), 'finished_at': finished.isoformat(),
                'execution': execution, 'reservation': reservation, 'amount_usd': '2.00',
                'reservation_count': count, 'billing_month': month,
                'observed_project_spend_usd': str(spend),
                'retained_allowances_usd': str(held),
                'conservative_monthly_total_usd': str(spend + held),
                'monthly_cap_usd': '8.00', 'within_cap': spend + held <= Decimal('8')
            }

def emit_snapshot(conn, logger):
    try:
        result = snapshot(conn)
        logger('BUDGET_DIAGNOSTIC: ' + json.dumps(result, sort_keys=True))
    except Exception:
        # Never log driver errors, connection strings or unexpected DB values.
        logger('BUDGET_DIAGNOSTIC: UNAVAILABLE')
