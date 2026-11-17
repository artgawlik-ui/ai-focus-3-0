import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from scripts.codex_automation import executor_admission as admission
from tests.automation.test_github_budget_transport import payload,BASE,API

class AdmissionBindingTests(unittest.TestCase):
    def env(self):
        p=payload()
        return dict(GITHUB_REPOSITORY=admission.transport.policy.REPO,
            GITHUB_REF='refs/heads/main',GITHUB_RUN_ATTEMPT='1',GITHUB_RUN_ID='123',
            GITHUB_SHA=BASE,APPROVED_BASE=BASE,APPROVED_NUMBER='40',
            APPROVED_DIGEST=p['digest'],APPROVED_BRANCH='codex/issue-40',MODEL='synthetic-model')

    def call(self,env=None,budget=2_000_000_000,path='/run/focus-codex-123-1'):
        admission.require_private_admission(self.env() if env is None else env,payload(),
            SimpleNamespace(model='synthetic-model',budget=budget),path,API())

    def test_exact_context_rechecks_receipt(self):
        with patch.object(admission.transport,'wait_receipt') as verify:
            self.call()
            self.assertEqual(verify.call_args.kwargs,{'timeout':1})
            self.assertEqual(verify.call_args.args[1],payload())

    def test_missing_or_changed_context_never_reads_receipt(self):
        for key in self.env():
            for value in (None,'wrong'):
                env=self.env()
                if value is None: del env[key]
                else: env[key]=value
                with self.subTest(key=key,value=value), patch.object(admission.transport,'wait_receipt') as verify:
                    with self.assertRaises(admission.transport.TransportBlocked):
                        self.call(env)
                    verify.assert_not_called()

    def test_state_directory_cannot_reset_other_run(self):
        with patch.object(admission.transport,'wait_receipt') as verify:
            with self.assertRaises(admission.transport.TransportBlocked):
                self.call(path='/run/focus-codex-other')
            verify.assert_not_called()

    def test_allowance_cannot_exceed_private_reservation(self):
        for amount in (0,True,2_000_000_001):
            with self.subTest(amount=amount),patch.object(admission.transport,'wait_receipt') as verify:
                with self.assertRaises(admission.transport.TransportBlocked):
                    self.call(budget=amount)
                verify.assert_not_called()

    def test_receipt_failure_propagates_without_fallback(self):
        with patch.object(admission.transport,'wait_receipt',side_effect=
                admission.transport.TransportBlocked('INVALID_PRIVATE_RECEIPT')):
            with self.assertRaisesRegex(admission.transport.TransportBlocked,'INVALID_PRIVATE_RECEIPT'):
                self.call()

    def test_production_checks_before_real_key_read(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parents[2]/'scripts/codex_automation/executor_limits.py').read_text()
        main=source.split('def main():')[1]
        self.assertLess(main.index('require_private_admission('),main.index('stdin.readline'))
