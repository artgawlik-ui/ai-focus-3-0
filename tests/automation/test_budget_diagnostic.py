import unittest
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal
from scripts.codex_automation.budget_diagnostic import snapshot, emit_snapshot, snapshot_attempt58, snapshot_attempt65

class DB:
    def __init__(self, rows):
        self.rows=iter(rows); self.calls=[]; self.parameters=[]
    def transaction(self): return nullcontext()
    def cursor(self): return nullcontext(self)
    def execute(self, sql, args=None): self.calls.append(sql); self.parameters.append(args)
    def fetchall(self): return next(self.rows)
    def fetchone(self): return next(self.rows)

class DiagnosticTests(unittest.TestCase):
    def test_missing_run_stops_before_reservation(self):
        db=DB([[]])
        self.assertEqual(snapshot(db), {'status':'UNVERIFIED_RUN'})
        self.assertEqual(len(db.calls),2)

    def test_missing_coverage_stops_before_reservation(self):
        d=datetime(2026,11,16,tzinfo=timezone.utc)
        db=DB([[(d,d.replace(hour=17))]])
        self.assertEqual(snapshot(db)['status'],'COSTS_NOT_COVERING_FINISH')
        self.assertEqual(len(db.calls),2)

    def rows(self, count=1):
        d=datetime(2026,11,17,tzinfo=timezone.utc)
        return [[(d,d.replace(day=16,hour=17))],
                [('reconciled','settled',Decimal('2'),'2026-11',Decimal('.03'))],
                (count,), (Decimal('2'),)]

    def test_settlement_retains_full_allowance(self):
        db=DB(self.rows()); result=snapshot(db)
        self.assertEqual(result['status'],'AUTOMATICALLY_RECONCILED')
        self.assertEqual(result['conservative_monthly_total_usd'],'2.03')
        self.assertTrue(result['within_cap'])
        self.assertIn('READ ONLY',db.calls[0])
        self.assertTrue(all(s.startswith(('SET TRANSACTION','SELECT')) for s in db.calls))

    def test_duplicates_fail_closed(self):
        self.assertEqual(snapshot(DB(self.rows(2)))['status'],'UNVERIFIED_SETTLEMENT')

    def test_no_error_details_logged(self):
        class Broken:
            def transaction(self): raise RuntimeError('secret-dsn')
        logs=[]; emit_snapshot(Broken(),logs.append)
        self.assertEqual(logs,['BUDGET_DIAGNOSTIC: UNAVAILABLE'])


class Attempt58Tests(unittest.TestCase):
    def test_absence_requires_both_tables_and_read_only(self):
        db=DB([(0,), (0,)])
        self.assertEqual(snapshot_attempt58(db)['status'],'NO_DURABLE_RECORDS')
        self.assertIn('READ ONLY', db.calls[0])
        self.assertEqual(len(db.calls),3)
        self.assertTrue(all(s.startswith(('SELECT','SET TRANSACTION')) for s in db.calls))

    def test_partial_or_duplicate_records_never_imply_absence(self):
        for pair in ((1,0),(0,1),(1,2),(2,1)):
            self.assertEqual(snapshot_attempt58(DB([(pair[0],),(pair[1],)]))['status'],
                             'INCONSISTENT_RECORDS')

    def test_present_hold_is_reported_without_claiming_cost_coverage(self):
        r=snapshot_attempt58(DB([(1,),(1,),[('awaiting_costs','reserved',Decimal('2'))]]))
        self.assertEqual(r['status'],'DURABLE_RECORDS_PRESENT')
        self.assertEqual(r['reservation'],'reserved')
        self.assertNotIn('costs_cover_finish',r)

    def test_broken_link_or_unexpected_values_are_not_logged(self):
        for rows in ([], [('SECRET','reserved',Decimal('2'))]):
            r=snapshot_attempt58(DB([(1,),(1,),rows]))
            self.assertEqual(r,{'status':'INCONSISTENT_RECORDS'})

class Attempt65Tests(unittest.TestCase):
    def test_actual_absence_requires_both_tables_for_exact_incident(self):
        db=DB([(0,), (0,)])
        self.assertEqual(snapshot_attempt65(db),
                         {'status':'NO_DURABLE_RECORDS','run_count':0,'reservation_count':0})
        self.assertEqual(db.parameters[1], ('44130029661:1',))
        self.assertEqual(db.parameters[2], ('github-run-44130029661:1',65))
        self.assertIn('READ ONLY',db.calls[0])
        self.assertTrue(all(s.startswith(('SELECT','SET TRANSACTION')) for s in db.calls))

    def test_partial_duplicates_and_invalid_counts_never_imply_absence(self):
        for runs,holds in ((1,0),(0,1),(2,1),(1,2),('secret',0),(True,0)):
            with self.subTest(runs=runs,holds=holds):
                result=snapshot_attempt65(DB([(runs,),(holds,)]))
                self.assertIn(result['status'],('INCONSISTENT_RECORDS','UNVERIFIED'))
                self.assertNotIn('secret',str(result))

    def test_present_hold_reports_only_validated_state_and_exact_join(self):
        db=DB([(1,), (1,), [('awaiting_costs','reserved',Decimal('2'))]])
        result=snapshot_attempt65(db)
        self.assertEqual(result,{'status':'DURABLE_RECORDS_PRESENT',
            'execution':'awaiting_costs','reservation':'reserved','amount_usd':'2.00'})
        self.assertEqual(db.parameters[-1],
                         ('44130029661:1',65,65,'github-run-44130029661:1'))
        self.assertTrue(all(s.startswith(('SELECT','SET TRANSACTION')) for s in db.calls))

    def test_bad_link_amount_or_state_is_never_logged(self):
        for rows in ([], [('secret','reserved',Decimal('2'))],
                     [('awaiting_costs','reserved',Decimal('3'))]):
            self.assertEqual(snapshot_attempt65(DB([(1,),(1,),rows])),
                             {'status':'INCONSISTENT_RECORDS'})

    def test_startup_emits_both_incidents_without_provider_or_writes(self):
        db=DB(DiagnosticTests().rows()+[(0,),(0,),(0,),(0,)])
        logs=[]; emit_snapshot(db,logs.append)
        import json
        result=json.loads(logs[0].split(': ',1)[1])
        self.assertEqual(result['attempt58']['status'],'NO_DURABLE_RECORDS')
        self.assertEqual(result['attempt65']['status'],'NO_DURABLE_RECORDS')
        self.assertTrue(all(s.startswith(('SELECT','SET TRANSACTION')) for s in db.calls))


if __name__ == '__main__': unittest.main()

