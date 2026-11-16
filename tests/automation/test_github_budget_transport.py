"""Synthetic authenticated API/ZIP fixtures; never contact GitHub/OpenAI/Render."""
import copy
from datetime import datetime, timezone, timedelta
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch
from urllib.error import HTTPError
from zipfile import ZipFile, ZipInfo

from scripts.codex_automation import github_budget_transport as t

NOW = datetime(2026,11,16,10,tzinfo=timezone.utc)
BASE = 'b'*40
ISSUE = {'number':40,'title':'Synthetic task','body':'Only synthetic data.',
         'state':'open','user':{'login':'artgawlik-ui'}}


def payload():
    return dict(version=1, repository=t.policy.REPO, run_id=123, attempt=1,
                issue=40, comment_id=456, digest=t.policy.digest(ISSUE), base=BASE, nonce='c'*64)


def archive(data=None, name='request.json', extra=False):
    buf = BytesIO()
    with ZipFile(buf, 'w') as z:
        z.writestr(name, json.dumps(payload()) if data is None else data)
        if extra:
            z.writestr('evil.py', 'raise RuntimeError()')
    return buf.getvalue()


class API:
    token = 'synthetic-only'

    def __init__(self):
        self.run = dict(id=123, run_attempt=1, event='issue_comment', path=t.WORKFLOW,
                        status='in_progress', head_branch='main', head_sha=BASE,
                        repository={'full_name':t.policy.REPO},
                        head_repository={'full_name':t.policy.REPO},
                        actor={'login':'artgawlik-ui'}, triggering_actor={'login':'artgawlik-ui'},
                        run_started_at=NOW.isoformat())
        self.job = dict(name='codex', run_id=123, run_attempt=1, head_sha=BASE,
                        status='in_progress', steps=[dict(
                            name='Wait for private PostgreSQL reservation receipt',
                            status='in_progress', conclusion=None, completed_at=None,
                            started_at=NOW.isoformat())])
        self.issue = copy.deepcopy(ISSUE)
        self.comment = dict(id=456, issue_url=f'https://api.github.com{t.PREFIX}/issues/40',
                            body='/codex approve '+t.policy.digest(self.issue),
                            user={'login':'artgawlik-ui'})
        self.claim = BASE
        self.role = 'admin'
        self.calls = []
        self.statuses = []
        self.artifacts = [dict(id=7, name='budget-request-123-1', expired=False)]
        self.total_count = 1

    def call(self, method, path, data=None):
        self.calls.append((method,path,data))
        if path == '/user':
            return {'login':t.RECEIPT_LOGIN}
        if method == 'POST' and '/statuses/' in path:
            receipt = dict(data, creator={'login':t.RECEIPT_LOGIN})
            self.statuses.insert(0, receipt)
            return receipt
        if '/commits/' in path and '/statuses?' in path:
            return self.statuses
        if '/workflows/' in path and '/runs?' in path:
            return {'workflow_runs':[self.run]}
        if path.endswith('/actions/runs/123/jobs?per_page=100'):
            return {'total_count':1,'jobs':[copy.deepcopy(self.job)]}
        if path.endswith('/actions/runs/123'):
            return copy.deepcopy(self.run)
        if '/artifacts?' in path:
            return {'total_count':self.total_count,'artifacts':self.artifacts}
        if path.endswith('/issues/comments/456'):
            return copy.deepcopy(self.comment)
        if path.endswith('/issues/40'):
            return copy.deepcopy(self.issue)
        if '/collaborators/' in path:
            return {'permission':self.role}
        if '/environments/' in path:
            return {'protection_rules':[{'type':'required_reviewers','reviewers':[
                {'type':'User','reviewer':{'login':'artgawlik-ui'}}]}]}
        if '/git/ref/' in path:
            return {'object':{'sha':self.claim}}
        raise AssertionError('Unexpected operation: '+path)


class TransportTests(unittest.TestCase):
    def test_default_off_before_credentials_or_database(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(t.policy,'API') as api:
            with self.assertRaisesRegex(t.TransportBlocked, '^PRIVATE_TRANSPORT_OFF$'):
                t.main(['--poll-once'])
            api.assert_not_called()

    def test_missing_controller_key_blocks_even_if_flag_is_on(self):
        with patch.dict(os.environ, {'FOCUS_PRIVATE_TRANSPORT_ENABLED':'true'}, clear=True):
            with self.assertRaisesRegex(t.TransportBlocked, 'PRIVATE_CONTROLLER_AUTH_REQUIRED'):
                t.main(['--poll-once'])

    def test_valid_request_bound_to_exact_approved_task(self):
        task = t.verify_request(API(), payload(), trusted_sha=BASE, now=NOW)
        self.assertEqual(task.run_id, '123:1')
        self.assertEqual(task.issue, 40)
        self.assertEqual(task.digest, t.policy.digest(ISSUE))

    def test_untrusted_run_fields_rejected_before_admission(self):
        changes = {'id':999,'run_attempt':2,'event':'pull_request','path':'evil.yml',
                   'head_branch':'untrusted','head_sha':'a'*40,'status':'completed',
                   'repository':{'full_name':'other/repo'},'head_repository':{'full_name':'other/repo'}}
        for key,value in changes.items():
            api=API(); api.run[key]=value
            with self.subTest(key=key), patch.object(t.lifecycle,'admit') as admit:
                with self.assertRaisesRegex(t.TransportBlocked, 'UNTRUSTED_WORKFLOW_RUN'):
                    t.handle_request(api, Mock(), payload(), trusted_sha=BASE, now=NOW)
                admit.assert_not_called()

    def test_stale_future_and_invalid_run_clock_block(self):
        for value in ((NOW-timedelta(minutes=16)).isoformat(),
                      (NOW+timedelta(seconds=1)).isoformat(), 'garbage', NOW.replace(tzinfo=None).isoformat()):
            api=API(); api.run['run_started_at']=value
            with self.subTest(value=value), self.assertRaisesRegex(t.TransportBlocked, 'STALE_WORKFLOW_REQUEST'):
                t.verify_request(api, payload(), trusted_sha=BASE, now=NOW)

    def test_changed_task_role_comment_and_claim_block(self):
        for kind in ('task','role','comment','claim','actor'):
            api=API()
            if kind=='task': api.issue['body']+=' changed'
            if kind=='role': api.role='read'
            if kind=='comment': api.comment['issue_url']='https://api.github.com/other'
            if kind=='claim': api.claim='a'*40
            if kind=='actor': api.run['triggering_actor']={'login':'intruder'}; api.role='read'
            with self.subTest(kind=kind), self.assertRaises((t.TransportBlocked,t.policy.Blocked)):
                t.verify_request(api, payload(), trusted_sha=BASE, now=NOW)

    def test_rerun_bad_identity_extra_fields_and_injection_block(self):
        for key,value in [('attempt',2),('attempt',True),('run_id','123'),('issue',True),
                          ('nonce','$(id)'),('base','../main'),('digest','a'*63),('extra','anything')]:
            data=payload(); data[key]=value
            with self.subTest(key=key), self.assertRaises((t.TransportBlocked,t.lifecycle.ExecutionBlocked)):
                t.validate(data)

    def test_zip_is_data_only_not_extracted_or_executed(self):
        self.assertEqual(t.decode_archive(archive()), payload())
        for data in (archive(name='../request.json'), archive(extra=True), archive(data='x'*5000),
                     b'x'*33000, b'not a zip', archive(data='{"version":1,"version":2}')):
            with self.subTest(size=len(data)), self.assertRaises(t.TransportBlocked):
                t.decode_archive(data)
        buf=BytesIO()
        with ZipFile(buf,'w') as z:
            info=ZipInfo('request.json'); info.external_attr=0o120777 << 16
            z.writestr(info,'target')
        with self.assertRaises(t.TransportBlocked):
            t.decode_archive(buf.getvalue())

    def test_receipt_only_after_private_commit_and_exact_context(self):
        api=API(); seen=[]
        with patch.object(t.lifecycle,'admit',side_effect=lambda *a,**k:seen.append('commit')):
            original=api.call
            def call(method,path,data=None):
                if method=='POST':
                    self.assertEqual(seen,['commit'])
                    self.assertEqual(data['context'],t.context(payload()))
                return original(method,path,data)
            api.call=call
            t.handle_request(api, Mock(), payload(), trusted_sha=BASE, now=NOW)
        self.assertEqual(sum(c[0]=='POST' for c in api.calls),1)

    def test_db_rejection_or_replay_cannot_post_success_receipt(self):
        api=API()
        with patch.object(t.lifecycle,'admit',side_effect=t.lifecycle.ExecutionBlocked('UNRECONCILED_EXECUTION')):
            with self.assertRaises(t.lifecycle.ExecutionBlocked):
                t.handle_request(api, Mock(), payload(), trusted_sha=BASE, now=NOW)
        self.assertFalse(any(c[0]=='POST' for c in api.calls))

    def test_ack_failure_does_not_release_committed_hold(self):
        api=API(); original=api.call
        def call(method,path,data=None):
            if method=='POST': raise t.policy.Blocked('GITHUB_NETWORK_FAILURE')
            return original(method,path,data)
        api.call=call
        with patch.object(t.lifecycle,'admit') as admit, patch.object(t.lifecycle,'finish') as finish:
            with self.assertRaises(t.policy.Blocked):
                t.handle_request(api, Mock(), payload(), trusted_sha=BASE, now=NOW)
            admit.assert_called_once(); finish.assert_not_called()

    def test_wrong_or_cross_run_receipt_never_admits_runner(self):
        valid={'context':t.context(payload()),'state':'success',
               'creator':{'login':t.RECEIPT_LOGIN},'description':'Private budget reservation committed',
               'target_url':f'https://github.com/{t.policy.REPO}/actions/runs/123'}
        api=API(); api.statuses=[valid]
        t.wait_receipt(api,payload())
        for key,value in [('state','failure'),('creator',{'login':'github-actions[bot]'}),
                          ('target_url','https://example.invalid'),('description','anything')]:
            api.statuses=[dict(valid,**{key:value})]
            with self.subTest(key=key),self.assertRaisesRegex(t.TransportBlocked,'INVALID_PRIVATE_RECEIPT'):
                t.wait_receipt(api,payload())
        api.statuses=[dict(valid,context='another-run')]
        clock=[0]
        def sleep(seconds): clock[0]+=seconds
        with self.assertRaisesRegex(t.TransportBlocked,'PRIVATE_RECEIPT_TIMEOUT'):
            t.wait_receipt(api,payload(),timeout=6,clock=lambda:clock[0],sleep=sleep)

    def test_artifact_poll_checks_run_id_expiry_and_complete_listing(self):
        for change in ('run','expired','incomplete'):
            api=API(); data=payload()
            if change=='run': data['run_id']=999
            if change=='expired': api.artifacts[0]['expired']=True
            if change=='incomplete': api.total_count=101
            with self.subTest(change=change),patch.object(t,'handle_request') as handle:
                with self.assertRaises(t.TransportBlocked):
                    t.poll_once(api,Mock(),trusted_sha=BASE,downloader=lambda *a:archive(json.dumps(data)))
                handle.assert_not_called()

    def test_finish_uses_github_terminal_state_not_local_success(self):
        api=API(); task=t.validate(payload())
        with patch.object(t.lifecycle,'finish') as finish:
            with self.assertRaisesRegex(t.TransportBlocked,'WORKFLOW_NOT_COMPLETED'):
                t.observe_finish(api,Mock(),task=task,now=NOW)
            finish.assert_not_called()
            api.run.update(status='completed',conclusion='cancelled')
            t.observe_finish(api,Mock(),task=task,now=NOW)
            self.assertEqual(finish.call_args.kwargs['outcome'],'cancelled')

    def test_redirect_never_forwards_administrative_or_github_auth(self):
        seen=[]
        def opener(req,timeout):
            seen.append(req)
            if len(seen)==1:
                raise HTTPError(req.full_url,302,'redirect',{'Location':'https://test.blob.core.windows.net/a?sig=synthetic'},None)
            return BytesIO(archive())
        self.assertEqual(t.decode_archive(t.download(API(),7,opener=opener)),payload())
        self.assertTrue(seen[0].has_header('Authorization'))
        self.assertFalse(seen[1].has_header('Authorization'))
        for url in ('http://test.blob.core.windows.net/a','https://evil.invalid/a',
                    'https://user:pass@test.blob.core.windows.net/a'):
            def rejected(req,timeout):
                raise HTTPError(req.full_url,302,'redirect',{'Location':url},None)
            with self.subTest(url=url),self.assertRaisesRegex(t.TransportBlocked,'ARTIFACT_REDIRECT_REJECTED'):
                t.download(API(),7,opener=rejected)

    def test_download_errors_are_fixed_codes(self):
        with self.assertRaisesRegex(t.TransportBlocked,'^ARTIFACT_DOWNLOAD_UNAVAILABLE$'):
            t.download(API(),7,opener=Mock(side_effect=OSError('SYNTHETIC_SECRET')))

    def test_private_controller_token_has_no_model_job_exposure(self):
        root=Path(__file__).resolve().parents[2]
        workflow=(root/'.github/workflows/codex-issues.yml').read_text()
        self.assertNotIn('FOCUS_BUDGET_GITHUB_TOKEN',workflow)
        self.assertIn('PRIVATE_ADMISSION_TRANSPORT_REQUIRED',workflow)

    def test_request_uses_trusted_job_outputs_not_downloaded_snapshot(self):
        previous=Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                event=Path('event.json')
                event.write_text(json.dumps({'action':'created','issue':{'number':40},'comment':{'id':456}}))
                Path('task').mkdir()
                Path('task/snapshot.json').write_text('{"number":999}')
                env={'FOCUS_PRIVATE_TRANSPORT_ENABLED':'true','GITHUB_REPOSITORY':t.policy.REPO,
                     'GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_ID':'123',
                     'GITHUB_EVENT_PATH':str(event),'APPROVED_NUMBER':'40','APPROVED_BASE':BASE,
                     'APPROVED_BRANCH':'codex/issue-40','APPROVED_DIGEST':t.policy.digest(ISSUE)}
                with patch.dict(os.environ,env,clear=True):
                    data=t.request_file()
                self.assertEqual(data['issue'],40)
                self.assertEqual(json.loads(Path('budget-request/request.json').read_text()),data)
            finally:
                os.chdir(previous)

    def test_wrong_controller_identity_cannot_reserve(self):
        api=API(); original=api.call
        api.call=lambda method,path,data=None: {'login':'intruder'} if path=='/user' else original(method,path,data)
        with patch.object(t.lifecycle,'admit') as admit:
            with self.assertRaisesRegex(t.TransportBlocked,'PRIVATE_CONTROLLER_IDENTITY_REQUIRED'):
                t.handle_request(api,Mock(),payload(),trusted_sha=BASE,now=NOW)
            admit.assert_not_called()

    def test_shutdown_before_loop_does_not_connect_or_touch_hold(self):
        stop=Mock(); stop.is_set.return_value=True
        connect,logger=Mock(),Mock()
        t.serve(API(),connect,trusted_sha=BASE,stop=stop,logger=logger)
        connect.assert_not_called(); logger.assert_not_called()

    def test_signal_during_refresh_stops_before_next_poll(self):
        stop=Mock(); stop.is_set.side_effect=[False,True]
        with patch.object(t,'refresh_runs',return_value=True) as refresh,patch.object(t,'poll_once') as poll:
            t.serve(API(),MagicMock(),trusted_sha=BASE,stop=stop,logger=Mock())
        refresh.assert_called_once()
        poll.assert_not_called()

    def test_signal_after_authorization_prevents_new_reservation(self):
        with patch.object(t.lifecycle,'admit') as admit:
            with self.assertRaisesRegex(t.TransportBlocked,'CONTROLLER_DRAINING'):
                t.handle_request(API(),Mock(),payload(),trusted_sha=BASE,now=NOW,accepting=lambda:False)
            admit.assert_not_called()

    def test_loop_failure_leaves_holds_and_exits_on_signal(self):
        stop=Mock(); stop.is_set.side_effect=[False,True]
        logger=Mock()
        with patch.object(t,'refresh_runs',side_effect=RuntimeError('SYNTHETIC_SECRET')),patch.object(t,'poll_once') as poll:
            t.serve(API(),Mock(),trusted_sha=BASE,stop=stop,logger=logger)
        poll.assert_not_called()
        logger.assert_called_once_with('BLOCKED: PRIVATE_CONTROLLER_FAILURE')
        stop.wait.assert_called_once_with(60)

    @unittest.skipUnless(os.getenv('GITHUB_ACTIONS')=='true' and os.getenv('DATABASE_URL'),
                         'PostgreSQL end-to-end runs only in isolated CI')
    def test_real_postgres_transport_lifecycle_without_external_calls(self):
        from urllib.parse import urlsplit
        import psycopg
        from scripts.codex_automation.durable_reservations import SCHEMA
        from decimal import Decimal
        url=os.environ['DATABASE_URL']; parsed=urlsplit(url)
        self.assertIn(parsed.hostname, ('localhost','127.0.0.1'))
        self.assertEqual(parsed.path,'/focus3_test')
        with psycopg.connect(url) as conn:
            with conn.transaction():
                conn.execute(SCHEMA.replace('CREATE TABLE IF NOT EXISTS','CREATE TEMP TABLE'))
                conn.execute(t.lifecycle.SCHEMA.replace('CREATE TABLE IF NOT EXISTS','CREATE TEMP TABLE'))
            api=API(); original=api.call
            def call(method,path,data=None):
                if method=='POST':
                    self.assertEqual(conn.info.transaction_status,psycopg.pq.TransactionStatus.IDLE)
                return original(method,path,data)
            api.call=call
            env={'OPENAI_COSTS_ADMIN_KEY':'synthetic','OPENAI_PROJECT_ID':'proj_test'}
            reader=lambda **kw:(Decimal('.03'),NOW-timedelta(hours=1))
            with patch.dict(os.environ,env):
                # Real PostgreSQL must remain empty if Costs I/O outlives wait.
                def closed_wait_reader(**kwargs):
                    api.job['steps'][0].update(status='completed',conclusion='failure')
                    return reader(**kwargs)
                with self.assertRaisesRegex(t.lifecycle.ExecutionBlocked,'TASK_AUTHORIZATION_REQUIRED'):
                    t.handle_request(api,conn,payload(),trusted_sha=BASE,now=NOW,reader=closed_wait_reader)
                with conn.transaction():
                    self.assertEqual(conn.execute('SELECT count(*) FROM codex_execution_runs').fetchone()[0],0)
                    self.assertEqual(conn.execute('SELECT count(*) FROM codex_budget_reservations').fetchone()[0],0)
                self.assertEqual(api.statuses,[])
                api.job['steps'][0].update(status='in_progress',conclusion=None)
                admitted=t.poll_once(api,conn,trusted_sha=BASE,now=NOW,reader=reader,
                                      downloader=lambda *a:archive())
                self.assertEqual(admitted,1)
                t.wait_receipt(api,payload())
                api.run.update(status='completed',conclusion='cancelled')
                with self.assertRaisesRegex(t.lifecycle.ExecutionBlocked,'COSTS_NOT_YET_COVERING_EXECUTION'):
                    t.refresh_runs(api,conn,now=NOW,reader=reader)
                with conn.transaction():
                    state=conn.execute('SELECT state FROM codex_budget_reservations').fetchone()[0]
                self.assertEqual(state,'reserved')
                later=NOW+timedelta(minutes=1)
                self.assertTrue(t.refresh_runs(api,conn,now=later,reader=lambda **kw:(Decimal('.10'),later)))
                with conn.transaction():
                    held=conn.execute('SELECT state,amount_usd FROM codex_budget_reservations').fetchone()
                self.assertEqual(held,('settled',Decimal('2')))
                api.run['status']='in_progress'
                with self.assertRaises(t.lifecycle.ExecutionBlocked):
                    t.handle_request(api,conn,payload(),trusted_sha=BASE,now=later,
                                     reader=lambda **kw:(Decimal('.10'),later))
                self.assertEqual(len(api.statuses),1)


class CostFailureLoggingTests(unittest.TestCase):
    def test_rate_limit_is_sanitized_and_backs_off_without_polling_or_receipt(self):
        for reason, expected in [('COSTS_RATE_LIMITED', 'COSTS_RATE_LIMITED'), ('SYNTHETIC_SECRET', 'COSTS_UNAVAILABLE')]:
            stop=Mock(); stop.is_set.side_effect=[False,True]
            logger=Mock()
            with patch.object(t,'refresh_runs',side_effect=t.CostGateBlocked(reason)), patch.object(t,'poll_once') as poll:
                t.serve(API(),MagicMock(),trusted_sha=BASE,stop=stop,logger=logger)
            logger.assert_called_once_with('BLOCKED: '+expected)
            stop.wait.assert_called_once_with(60)
            poll.assert_not_called()


class ReceiptWindowTests(unittest.TestCase):
    def test_closed_or_wrong_wait_cannot_authorize(self):
        changes = [dict(status='completed'), dict(run_id=999), dict(run_attempt=2),
                   dict(head_sha='a'*40), dict(steps=[]), dict(steps=None)]
        for change in changes:
            api=API(); api.job.update(change)
            with self.subTest(change=change), self.assertRaises(t.TransportBlocked):
                t.verify_waiting_job(api,payload(),now=NOW)
        for change in [dict(status='completed',conclusion='failure'),
                       dict(completed_at=NOW.isoformat()),dict(conclusion='cancelled'),
                       dict(started_at='invalid'),dict(started_at=NOW.replace(tzinfo=None).isoformat()),
                       dict(started_at=(NOW+timedelta(seconds=1)).isoformat())]:
            api=API(); api.job['steps'][0].update(change)
            with self.subTest(step=change), self.assertRaises(t.TransportBlocked):
                t.verify_waiting_job(api,payload(),now=NOW)

    def test_wait_window_is_bounded_before_runner_timeout(self):
        t.verify_waiting_job(API(),payload(),now=NOW+timedelta(seconds=89))
        for elapsed in (90,119,120,121):
            with self.subTest(elapsed=elapsed),self.assertRaisesRegex(t.TransportBlocked,'RECEIPT_ADMISSION_WINDOW_CLOSED'):
                t.verify_waiting_job(API(),payload(),now=NOW+timedelta(seconds=elapsed))

    def test_ambiguous_or_incomplete_jobs_fail_closed(self):
        for response in [{'total_count':2,'jobs':[API().job]},
                         {'total_count':2,'jobs':[API().job,API().job]},
                         {'total_count':0,'jobs':[]}, {'total_count':1,'jobs':None}]:
            api=API(); original=api.call
            api.call=lambda method,path,data=None: response if '/jobs?' in path else original(method,path,data)
            with self.subTest(response=response),self.assertRaises(t.TransportBlocked):
                t.verify_waiting_job(api,payload(),now=NOW)

    def test_wait_ending_during_cost_read_creates_no_hold_or_receipt(self):
        from decimal import Decimal
        api=API(); conn=MagicMock()
        cur=conn.cursor.return_value.__enter__.return_value
        def reader(**kwargs):
            api.job['steps'][0].update(status='completed',conclusion='failure',completed_at=NOW.isoformat())
            return Decimal('.03'),NOW
        env={'OPENAI_COSTS_ADMIN_KEY':'synthetic','OPENAI_PROJECT_ID':'proj_test'}
        with patch.dict(os.environ,env),self.assertRaisesRegex(t.lifecycle.ExecutionBlocked,'TASK_AUTHORIZATION_REQUIRED'):
            t.handle_request(api,conn,payload(),trusted_sha=BASE,now=NOW,reader=reader)
        self.assertFalse(any('INSERT' in c.args[0] for c in cur.execute.call_args_list))
        self.assertEqual(api.statuses,[])

    def test_wait_ending_after_commit_withholds_ack_and_preserves_hold(self):
        api=API()
        def committed(*args,**kwargs):
            api.job['status']='completed'
        with patch.object(t.lifecycle,'admit',side_effect=committed) as admit, patch.object(t.lifecycle,'finish') as finish:
            with self.assertRaisesRegex(t.TransportBlocked,'ACTIVE_RECEIPT_WAIT_REQUIRED'):
                t.handle_request(api,Mock(),payload(),trusted_sha=BASE,now=NOW)
            admit.assert_called_once(); finish.assert_not_called()
        self.assertEqual(api.statuses,[])

    def test_live_clock_is_checked_after_github_io(self):
        api=API(); original=api.call; events=[]
        def call(*args,**kwargs):
            events.append('api')
            return original(*args,**kwargs)
        def clock(now):
            events.append('clock')
            return NOW+timedelta(seconds=90)
        api.call=call
        with patch.object(t.lifecycle,'utc',side_effect=clock), self.assertRaisesRegex(t.TransportBlocked,'RECEIPT_ADMISSION_WINDOW_CLOSED'):
            t.verify_waiting_job(api,payload())
        self.assertEqual(events,['api','clock'])
