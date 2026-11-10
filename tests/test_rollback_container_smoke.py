"""Safety of the image smoke harness itself; no Docker or external network needed."""
import json
import subprocess
import pytest
from tests import rollback_container_smoke as smoke


def test_synthetic_environment_never_inherits_app_secrets_or_production_url(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://do-not-use.invalid/private')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-forbidden-input')
    monkeypatch.setenv('META_APP_SECRET', 'synthetic-forbidden-input')
    monkeypatch.setenv('HTTPS_PROXY', 'https://do-not-use.invalid')
    env = smoke.synthetic_environment()
    assert env['DATABASE_URL'] == 'postgresql://postgres@db/focus3_rollback_smoke'
    assert 'OPENAI_API_KEY' not in env and 'META_APP_SECRET' not in env
    assert all(env[name] == '' for name in smoke.PROXIES)
    assert all(env[name] == 'true' for name in smoke.POISON)
    assert 'FOCUS_READONLY_ROLLBACK_APPROVED' not in env


def test_docker_cannot_be_redirected_to_an_inherited_remote_context(monkeypatch):
    for name in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'):
        monkeypatch.setenv(name, 'synthetic-remote')
    monkeypatch.setenv('DOCKER_CONFIG', '/synthetic/config-selector')
    env = smoke.docker_environment()
    assert not any(name in env for name in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS',
                                          'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'))
    assert env['DOCKER_CONFIG'] == '/synthetic/config-selector'


def test_docker_failure_never_exposes_raw_exception_or_environment(monkeypatch, capsys):
    def denied(command, **kwargs):
        assert command[:2] == ['docker', '--host=unix:///var/run/docker.sock']
        return subprocess.CompletedProcess(command, 1, 'synthetic-private-output', 'synthetic-private-error')
    monkeypatch.setattr(subprocess, 'run', denied)
    with pytest.raises(smoke.SmokeError, match='^DOCKER_COMMAND_FAILED$') as error:
        smoke.Docker().run('info')
    assert 'private' not in str(error.value)
    assert capsys.readouterr() == ('', '')


def test_cleanup_never_removes_a_resource_with_another_label():
    docker = smoke.Docker()
    docker.containers = ['synthetic-id']
    calls = []
    def command(*args, **kwargs):
        calls.append(args)
        if args[:2] == ('container', 'ls'):
            return ''
        return json.dumps([{'Config': {'Labels': {'focus.issue14': 'someone-else'}}}])
    docker.run = command
    with pytest.raises(AssertionError):
        docker.cleanup()
    assert not any('rm' in args for args in calls)


def test_fingerprints_cover_exact_native_21_tables_in_a_single_statement():
    query = smoke.fingerprint_sql()
    assert len(smoke.TABLE_NAMES) == len(set(smoke.TABLE_NAMES)) == 21
    assert query.count(' AS table_name,') == 21
    assert 'sha256(convert_to' in query and 'COLLATE "C"' in query
    assert query.count(';') == 0 and query.count(' UNION ALL ') == 20
    assert all('FROM public."' + name + '" t' in query for name in smoke.TABLE_NAMES)
