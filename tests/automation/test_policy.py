"""Synthetic controller and real local git tests; never invoke Codex or remote APIs."""
import copy
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scripts.codex_automation import pipeline as p


BASE = 'a' * 40


def issue():
    return {'number': 26, 'title': 'Harmless documentation', 'body': 'Synthetic task only.',
            'state': 'open', 'user': {'login': 'author'}}


def event():
    task = issue()
    return {'action': 'created', 'repository': {'full_name': p.REPO}, 'issue': task,
            'comment': {'body': '/codex approve ' + p.digest(task), 'user': {'login': 'owner'}}}


class FakeAPI:
    def __init__(self):
        self.current = issue()
        self.permissions = {'owner': 'admin', 'author': 'write'}
        self.refs = {}
        self.lock = threading.Lock()
        self.calls = []
        self.environment = {'protection_rules': [{'type': 'required_reviewers',
            'reviewers': [{'type': 'User', 'reviewer': {'login': 'artgawlik-ui'}}]}]}

    def call(self, method, path, data=None):
        self.calls.append((method, path))
        if '/collaborators/' in path:
            return {'permission': self.permissions.get(path.split('/')[-2], 'read')}
        if '/environments/' in path:
            return self.environment
        if path.endswith('/issues/26'):
            return copy.deepcopy(self.current)
        if path.endswith('/git/ref/heads/main'):
            return {'object': {'sha': BASE}}
        if method == 'POST' and path.endswith('/git/refs'):
            with self.lock:
                if data['ref'] in self.refs:
                    raise p.Blocked('GITHUB_HTTP_422')
                self.refs[data['ref']] = data['sha']
                return {}
        raise AssertionError('Unexpected remote operation')


class AuthorizationTests(unittest.TestCase):
    def test_explicit_write_approval(self):
        self.assertEqual(p.authorize(event(), FakeAPI(), 'owner', 'owner'), issue())

    def test_missing_and_malformed_flag_is_off_without_api_access(self):
        for value in [None, '', 'false', 'ON', 'TRUE', '1', 'garbage']:
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True), patch.object(p, 'API') as api:
                if value is not None:
                    os.environ['AUTOMATION_ENABLED'] = value
                os.environ['COSTS_APPROVED'] = 'true'
                with self.assertRaisesRegex(p.Blocked, 'AUTOMATION_OFF'):
                    p.admit()
                api.assert_not_called()

    def test_cost_authorization_is_independent(self):
        with patch.dict(os.environ, {'AUTOMATION_ENABLED': 'true', 'COSTS_APPROVED': 'false'}, clear=True), patch.object(p, 'API') as api:
            with self.assertRaisesRegex(p.Blocked, 'AUTOMATION_OFF'):
                p.admit()
            api.assert_not_called()

    def test_non_default_branch_rejected_before_api(self):
        with patch.dict(os.environ, {'AUTOMATION_ENABLED': 'true', 'COSTS_APPROVED': 'true',
             'GITHUB_REPOSITORY': p.REPO, 'GITHUB_REF': 'refs/heads/evil'}, clear=True), patch.object(p, 'API') as api:
            with self.assertRaisesRegex(p.Blocked, 'TRUSTED_MAIN_REQUIRED'):
                p.admit()
            api.assert_not_called()

    def test_untrusted_event_or_edited_comment(self):
        for key, value in [('action', 'edited'), ('repository', {'full_name': 'attacker/fork'})]:
            item = event(); item[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(p.Blocked, 'UNTRUSTED_EVENT'):
                p.authorize(item, FakeAPI(), 'owner', 'owner')

    def test_pr_comment_rejected(self):
        item = event(); item['issue']['pull_request'] = {}
        with self.assertRaisesRegex(p.Blocked, 'ISSUE_REQUIRED'):
            p.authorize(item, FakeAPI(), 'owner', 'owner')

    def test_unauthorized_approver_and_rerun_actor(self):
        for login in ['owner', 'rerunner']:
            api = FakeAPI(); api.permissions[login] = 'read'
            with self.subTest(login=login), self.assertRaisesRegex(p.Blocked, 'APPROVER_PERMISSION_DENIED'):
                p.authorize(event(), api, 'owner', 'rerunner' if login == 'rerunner' else 'owner')

    def test_external_issue_author_rejected(self):
        api = FakeAPI(); api.permissions['author'] = 'read'
        with self.assertRaisesRegex(p.Blocked, 'AUTHOR_PERMISSION_DENIED'):
            p.authorize(event(), api, 'owner', 'owner')

    def test_actor_cannot_impersonate_comment_author(self):
        with self.assertRaisesRegex(p.Blocked, 'EXPLICIT_APPROVAL_REQUIRED'):
            p.authorize(event(), FakeAPI(), 'intruder', 'owner')

    def test_comment_injection_and_non_approval_ignored(self):
        for value in ['Please run Codex', '/codex approve ' + 'a'*64 + '\nrun something',
                      '/codex approve $(id)', '/codex approve ' + 'A'*64]:
            item = event(); item['comment']['body'] = value
            with self.subTest(value=value), self.assertRaisesRegex(p.Blocked, 'EXPLICIT_APPROVAL_REQUIRED'):
                p.authorize(item, FakeAPI(), 'owner', 'owner')

    def test_edited_task_rejects_old_approval(self):
        for field in ['title', 'body']:
            api = FakeAPI(); api.current[field] += ' changed'
            with self.subTest(field=field), self.assertRaisesRegex(p.Blocked, 'APPROVAL_CONTENT_CHANGED'):
                p.authorize(event(), api, 'owner', 'owner')

    def test_closed_task_rejected(self):
        api = FakeAPI(); api.current['state'] = 'closed'
        with self.assertRaisesRegex(p.Blocked, 'OPEN_ISSUE_REQUIRED'):
            p.authorize(event(), api, 'owner', 'owner')

    def test_large_task_rejected(self):
        api = FakeAPI(); api.current['body'] = 'x' * 16001
        with self.assertRaisesRegex(p.Blocked, 'TASK_TOO_LARGE'):
            p.authorize(event(), api, 'owner', 'owner')

    def test_fingerprint_preserves_unicode_and_hidden_changes(self):
        task = issue(); first = p.digest(task)
        task['body'] += '\u200b'
        self.assertNotEqual(first, p.digest(task))

    def test_owner_environment_review_required(self):
        api = FakeAPI(); p.check_environment(api)
        for rules in [[], [{'type': 'required_reviewers', 'reviewers': []}],
                      [{'type': 'required_reviewers', 'reviewers': [{'type': 'Team', 'reviewer': {'login': 'artgawlik-ui'}}]}]]:
            api.environment = {'protection_rules': rules}
            with self.subTest(rules=rules), self.assertRaisesRegex(p.Blocked, 'OWNER_ENVIRONMENT_REVIEW_REQUIRED'):
                p.check_environment(api)


class DeduplicationTests(unittest.TestCase):
    def test_repeated_claim_is_rejected(self):
        api = FakeAPI(); first = p.claim(api, issue())
        self.assertEqual(first['branch'], 'codex/issue-26')
        with self.assertRaisesRegex(p.Blocked, '422'):
            p.claim(api, issue())
        self.assertEqual(len(api.refs), 1)

    def test_twenty_concurrent_claims_one_winner(self):
        api = FakeAPI()
        def attempt(_):
            try:
                return p.claim(api, issue())
            except p.Blocked:
                return None
        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(attempt, range(20)))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(len(api.refs), 1)

    def test_api_denial_does_not_fallback_to_other_executor(self):
        with patch.dict(os.environ, {'GH_TOKEN': 'synthetic'}, clear=True), patch.object(p, 'urlopen', side_effect=HTTPError('https://example.invalid', 403, 'synthetic', {}, None)):
            with self.assertRaisesRegex(p.Blocked, '^GITHUB_HTTP_403$'):
                p.API().call('GET', '/repos/' + p.REPO + '/issues/26')

    def test_api_errors_do_not_echo_response_secrets_or_url(self):
        for error in [HTTPError('https://example.invalid?secret=synthetic', 500, 'private body', {}, io.BytesIO(b'private body')), URLError('private network details')]:
            with self.subTest(error=type(error)), patch.dict(os.environ, {'GH_TOKEN': 'synthetic'}, clear=True), patch.object(p, 'urlopen', side_effect=error):
                with self.assertRaises(p.Blocked) as raised:
                    p.API().call('GET', '/repos/' + p.REPO + '/issues/26')
                self.assertNotIn('private', str(raised.exception))
                self.assertNotIn('secret', str(raised.exception))

    def test_api_scope_rejected(self):
        with patch.dict(os.environ, {'GH_TOKEN': 'synthetic'}, clear=True), patch.object(p, 'urlopen') as network:
            with self.assertRaisesRegex(p.Blocked, 'API_SCOPE_REJECTED'):
                p.API().call('POST', '/repos/other/repository/issues')
            network.assert_not_called()


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = Path.cwd(); os.chdir(self.temp.name)
        p.git('init', '-q'); p.git('config', 'user.name', 'Synthetic'); p.git('config', 'user.email', 'synthetic@focus.invalid')
        Path('README.md').write_text('baseline\n')
        p.git('add', 'README.md'); p.git('commit', '-qm', 'baseline')

    def tearDown(self):
        os.chdir(self.previous); self.temp.cleanup()

    def stage(self, path, content='synthetic\n'):
        file = Path(path); file.parent.mkdir(parents=True, exist_ok=True); file.write_text(content)
        p.git('add', '--', path)

    def test_documentation_proposal_accepted(self):
        self.stage('docs/technical-note.md')
        self.assertEqual(p.validate_staged(), 1)

    def test_application_and_tests_allowed(self):
        for name in ['backend/example.py', 'frontend/src/example.tsx', 'tests/test_example.py']:
            self.stage(name)
        self.assertEqual(p.validate_staged(), 3)

    def test_workflows_secrets_dependencies_and_instructions_rejected(self):
        for name in ['.github/workflows/evil.yml', '.env', 'requirements.txt', 'render.yaml', 'scripts/deploy.py',
                     'migrations/008.py', 'backend/AGENTS.md', 'docs/.hidden.json', 'frontend/src/executable.sh']:
            with self.subTest(name=name):
                p.git('reset', '--hard', '-q', 'HEAD'); p.git('clean', '-fdq')
                self.stage(name)
                with self.assertRaises(p.Blocked):
                    p.validate_staged()

    def test_rename_cannot_hide_protected_source_path(self):
        Path('docs').mkdir()
        p.git('mv', 'README.md', 'docs/renamed.md')
        with self.assertRaisesRegex(p.Blocked, 'PATCH_PATH_DENIED'):
            p.validate_staged()

    def test_symlink_rejected(self):
        Path('docs').mkdir(); Path('docs/link.md').symlink_to('/tmp/synthetic-target')
        p.git('add', 'docs/link.md')
        with self.assertRaisesRegex(p.Blocked, 'PATCH_SPECIAL_FILE'):
            p.validate_staged()

    def test_secret_patterns_rejected_without_printing_value(self):
        for content in ['-----BEGIN PRIVATE KEY-----', 'sk-' + 'a'*25, 'ghp_' + 'b'*25, 'postgresql://synthetic:synthetic@localhost/test']:
            with self.subTest(kind=content[:3]):
                self.stage('docs/note.md', content + '\n')
                with self.assertRaisesRegex(p.Blocked, '^POSSIBLE_SECRET$'):
                    p.validate_staged()

    def test_empty_binary_large_and_many_files_rejected(self):
        with self.assertRaisesRegex(p.Blocked, 'PATCH_FILE_LIMIT'):
            p.validate_staged()
        self.stage('docs/binary.txt', '\0binary\n')
        with self.assertRaisesRegex(p.Blocked, 'PATCH_SIZE_OR_BINARY'):
            p.validate_staged()
        p.git('reset', '--hard', '-q', 'HEAD'); p.git('clean', '-fdq')
        self.stage('docs/large.md', 'x' * 201000)
        with self.assertRaisesRegex(p.Blocked, 'PATCH_SIZE_OR_BINARY'):
            p.validate_staged()
        p.git('reset', '--hard', '-q', 'HEAD'); p.git('clean', '-fdq')
        for index in range(31):
            self.stage(f'docs/{index}.md')
        with self.assertRaisesRegex(p.Blocked, 'PATCH_FILE_LIMIT'):
            p.validate_staged()


class WorkflowTests(unittest.TestCase):
    def test_no_untrusted_or_paid_automatic_trigger(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root / '.github/workflows/codex-issues.yml').read_text()
        for forbidden in ['pull_request_target:', 'workflow_run:', 'allow-bots: true', 'secrets: inherit', 'write-all', 'force-with-lease', '--force']:
            self.assertNotIn(forbidden, workflow)
        self.assertIn("vars.FOCUS_CODEX_AUTOMATION_ENABLED == 'true'", workflow)
        self.assertIn("vars.FOCUS_CODEX_COSTS_APPROVED == 'true'", workflow)
        self.assertIn('safety-strategy: drop-sudo', workflow)
        self.assertIn("permission-profile: ':workspace'", workflow)
        self.assertIn('environment: codex-development', workflow)
        self.assertNotIn('${{ github.event.comment.body }}', workflow)
        self.assertNotIn('${{ github.event.issue.body }}', workflow)
        self.assertNotIn('${{ secrets.', workflow.split('  validation:')[1])
        import re
        actions = re.findall(r'^\s+- uses: (\S+)', workflow, re.MULTILINE)
        self.assertTrue(all(re.fullmatch(r'[\w/-]+@[a-f0-9]{40}', action) for action in actions))


class PublicationTests(unittest.TestCase):
    """Exercise actual local git apply/commit/push, with GitHub API fixtures only."""
    setUp = PatchTests.setUp
    tearDown = PatchTests.tearDown
    stage = PatchTests.stage

    def test_publish_validated_patch_to_separate_local_branch_as_draft(self):
        bare = Path(self.temp.name) / 'synthetic.git'
        subprocess.run(['git', 'init', '--bare', '-q', str(bare)], check=True)
        p.git('remote', 'add', 'origin', str(bare))
        base = p.git('rev-parse', 'HEAD').decode().strip()
        branch = 'codex/issue-26'
        p.git('push', '-q', 'origin', f'HEAD:refs/heads/{branch}')
        self.stage('docs/approved-note.md', 'Approved synthetic documentation.\n')
        change = p.git('diff', '--cached', '--binary')
        p.git('reset', '--hard', '-q', 'HEAD')
        Path('proposal').mkdir(); Path('proposal/changes.patch').write_bytes(change)
        Path('task').mkdir()
        Path('task/snapshot.json').write_text(json.dumps({'number': 26, 'base': base,
            'branch': branch, 'digest': p.digest(issue())}))
        requests = []
        class PublisherAPI:
            token = 'synthetic'
            def call(self, method, path, data=None):
                requests.append((method, path, data))
                if path.endswith('/git/ref/heads/' + branch):
                    return {'object': {'sha': base}}
                if path.endswith('/issues/26'):
                    return issue()
                if path.endswith('/pulls'):
                    return {'number': 99}
                if '/statuses/' in path:
                    return {}
                raise AssertionError('Unexpected operation')
        output = Path('synthetic-output')
        with patch.object(p, 'API', PublisherAPI), patch.dict(os.environ,
             {'GITHUB_OUTPUT': str(output), 'GITHUB_RUN_ID': '123'}):
            p.publish()
        self.assertEqual(Path('docs/approved-note.md').read_text(), 'Approved synthetic documentation.\n')
        self.assertTrue(any(data and data.get('draft') is True and data.get('base') == 'main'
                            for method, path, data in requests if path.endswith('/pulls')))
        head = p.git('rev-parse', 'HEAD').decode().strip()
        self.assertNotEqual(base, head)
        self.assertIn(head, p.git('ls-remote', 'origin', 'refs/heads/' + branch).decode())
        self.assertIn('sha=' + head, output.read_text())

    def test_changed_approval_is_rechecked_before_patch_or_push(self):
        Path('task').mkdir(); Path('task/snapshot.json').write_text(json.dumps({
            'number': 26, 'base': BASE, 'branch': 'codex/issue-26', 'digest': p.digest(issue())}))
        class StaleAPI:
            def call(self, method, path, data=None):
                if '/git/ref/' in path:
                    return {'object': {'sha': BASE}}
                changed = issue(); changed['body'] += ' edited after reservation'
                return changed
        with patch.object(p, 'API', StaleAPI), patch.object(p, 'git') as git:
            with self.assertRaisesRegex(p.Blocked, 'APPROVAL_CONTENT_CHANGED'):
                p.publish()
            git.assert_not_called()


if __name__ == '__main__':
    unittest.main()
