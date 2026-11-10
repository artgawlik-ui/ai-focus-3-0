"""Boot the built image on an isolated Docker network. Stdlib only; no host DB URL."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid
from scripts.release_selects import TABLES

ROOT = Path(__file__).resolve().parents[1]
TABLE_NAMES = tuple(sorted(TABLES + ('focus_contact_policies', 'focus_work_settings',
                                   'focus_tasks', 'focus_notifications')))
PROXIES = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy')
POISON = ('META_ENABLED', 'META_OAUTH_ENABLED', 'META_WEBHOOK_VERIFY_ENABLED',
          'META_INGEST_ENABLED', 'META_CRM_HISTORY_ENABLED', 'META_DIAGNOSTICS_ENABLED',
          'META_DM_TRANSPORT_ENABLED', 'GOOGLE_SCHEMA_ENABLED', 'GOOGLE_CALENDAR_ENABLED',
          'GOOGLE_CALENDAR_WRITE_ENABLED', 'FOCUS_CALENDAR_SCHEMA_ENABLED',
          'FOCUS_CALENDAR_ENABLED', 'FOCUS_DIAGNOSTICS_ENABLED', 'AI_PAID_PROCESSING_APPROVED',
          'OFFSITE_BACKUP_ENABLED', 'AGENT_V2_ENABLED')


class SmokeError(RuntimeError):
    pass


def docker_environment():
    # Select only the managed local daemon. Preserve Docker config/registry credentials.
    return {k: v for k, v in os.environ.items() if k not in
            ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')}


def synthetic_environment():
    # Construct from scratch: never inherit DATABASE_URL, cookies, keys or app credentials.
    return {'APP_ENV': 'test', 'DATABASE_URL': 'postgresql://postgres@db/focus3_rollback_smoke',
            'PORT': '8000', 'WORKER_PAUSED': 'false',
            **{name: 'true' for name in POISON}, **{name: '' for name in PROXIES},
            'NO_PROXY': '*', 'no_proxy': '*'}


def fingerprint_sql():
    parts = []
    for table in TABLE_NAMES:
        assert re.fullmatch('[a-z_]+', table)
        parts.append("SELECT '" + table + "' AS table_name,count(*) AS row_count,"
            "encode(sha256(convert_to(coalesce(string_agg(to_jsonb(t)::text,E'\\n' "
            "ORDER BY to_jsonb(t)::text COLLATE \"C\"),''),'UTF8')),'hex') AS sha256 "
            'FROM public."' + table + '" t')
    return 'SELECT json_agg(f ORDER BY table_name) FROM (' + ' UNION ALL '.join(parts) + ') f'


class Docker:
    def __init__(self):
        self.label = 'focus.issue14=' + uuid.uuid4().hex
        self.containers = []
        self.network = None

    def run(self, *args, stdin=None, timeout=30, combined=False):
        try:
            result = subprocess.run(['docker', '--host=unix:///var/run/docker.sock', *args],
                input=stdin, text=True, capture_output=True, timeout=timeout, env=docker_environment())
        except (OSError, subprocess.TimeoutExpired):
            raise SmokeError('DOCKER_COMMAND_UNAVAILABLE_OR_TIMEOUT') from None
        if result.returncode:
            # Docker/driver stderr can include environment data. Never expose it.
            raise SmokeError('DOCKER_COMMAND_FAILED')
        return (result.stdout + (result.stderr if combined else '')).strip()

    def image(self, name):
        data = json.loads(self.run('image', 'inspect', name))[0]
        assert re.fullmatch(r'sha256:[0-9a-f]{64}', data['Id'])
        return data

    def container(self, image, *args):
        identifier = self.run('run', '--detach', '--pull=never', '--label', self.label,
                              '--network', self.network, *args, image)
        assert re.fullmatch('[0-9a-f]{64}', identifier)
        self.containers.append(identifier)
        return identifier

    def sql(self, pg, statement):
        return self.run('exec', '-i', pg, 'psql', '-XAt', '--set', 'ON_ERROR_STOP=1',
                        '--host', '127.0.0.1', '--username', 'postgres',
                        '--dbname', 'focus3_rollback_smoke', stdin=statement)

    def snapshot(self, pg):
        value = json.loads(self.sql(pg, fingerprint_sql()))
        assert [row['table_name'] for row in value] == list(TABLE_NAMES)
        return value

    def cleanup(self):
        # Never prune shared resources. Remove only IDs created here with the exact private label.
        # Include fixture containers if a timed-out docker CLI left one behind.
        found = self.run('container', 'ls', '--all', '--quiet', '--no-trunc',
                         '--filter', 'label=' + self.label).splitlines()
        for identifier in reversed(list(dict.fromkeys(self.containers + found))):
            data = json.loads(self.run('container', 'inspect', identifier))[0]
            assert data['Config']['Labels'].get('focus.issue14') == self.label.split('=', 1)[1]
            self.run('container', 'rm', '--force', identifier)
        if self.network:
            data = json.loads(self.run('network', 'inspect', self.network))[0]
            assert data['Labels'].get('focus.issue14') == self.label.split('=', 1)[1]
            self.run('network', 'rm', self.network)


def execute(image_name, results):
    docker = Docker()
    report = {'container_runtime': 'BLOCKED', 'render_artifact_availability': 'BLOCKED',
              'production_handoff': 'BLOCKED', 'checks': []}
    try:
        report['stage'] = 'inspect_local_images'
        image = docker.image(image_name)
        assert image['Config']['Cmd'] == ['python', '-m', 'scripts.rollback_readonly']
        assert image['Config']['User'] == 'focus' and not image['Config'].get('Entrypoint')
        pg_image = docker.image('postgres:17')  # CI already pulled the existing service image.
        report.update(image_id=image['Id'], postgres_image_id=pg_image['Id'])
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                           text=True, timeout=5).strip()
        assert re.fullmatch('[0-9a-f]{40}', revision)
        report['tested_checkout_commit'] = revision
        report['stage'] = 'create_synthetic_network_and_pg'
        docker.network = docker.run('network', 'create', '--internal', '--label', docker.label,
                                    'focus-issue14-' + uuid.uuid4().hex)
        net = json.loads(docker.run('network', 'inspect', docker.network))[0]
        assert net['Internal'] is True
        pg = docker.container(pg_image['Id'], '--network-alias', 'db', '--memory=512m', '--cpus=1',
            '--pids-limit=100', '--tmpfs', '/var/lib/postgresql/data:rw,nosuid,size=192m',
            '--env', 'POSTGRES_HOST_AUTH_METHOD=trust', '--env', 'POSTGRES_DB=focus3_rollback_smoke',
            *sum((['--env', name + '='] for name in PROXIES), []))
        end = time.monotonic() + 15
        while True:
            try:
                docker.sql(pg, 'SELECT 1;')
                break
            except SmokeError:
                assert time.monotonic() < end, 'synthetic_pg_readiness'
                time.sleep(.1)
        assert docker.sql(pg, "SELECT current_setting('server_version_num')::integer/10000") == '17'
        with tempfile.TemporaryDirectory(prefix='focus-issue14-') as temporary:
            env_file = Path(temporary, 'synthetic.env')
            env_file.touch(mode=0o600)
            env_file.write_text(''.join(k + '=' + v + '\n' for k, v in synthetic_environment().items()))
            common = ['--pull=never', '--network', docker.network, '--label', docker.label,
                      '--env-file', str(env_file), '--read-only', '--tmpfs', '/tmp:rw,nosuid,size=16m',
                      '--cap-drop=ALL', '--security-opt=no-new-privileges', '--memory=512m',
                      '--cpus=1', '--pids-limit=64']
            # Fixture preparation alone gets migration files, read-only. API gets no mounts.
            report['stage'] = 'prepare_synthetic_schema_007'
            docker.run('run', '--rm', *common,
                '--mount', f'type=bind,src={ROOT / "migrations"},dst=/app/migrations,readonly',
                '--mount', f'type=bind,src={ROOT / "native-alembic.ini"},dst=/app/native-alembic.ini,readonly',
                '--entrypoint', 'python', image['Id'], '-m', 'alembic', '-c', 'native-alembic.ini',
                'upgrade', 'head', timeout=45)
            probe = (ROOT / 'tests/fixtures/rollback_container_probe.py').read_text()
            report['stage'] = 'seed_synthetic_accounts_and_canaries'
            docker.run('run', '--rm', '-i', *common, '--entrypoint', 'python', image['Id'], '-',
                       'seed', stdin=probe)
            before = docker.snapshot(pg)
            assert len(before) == 21
            assert docker.sql(pg, 'SELECT version_num FROM alembic_version') == '007'
            # No override of CMD/entrypoint: this is the built emergency image itself.
            report['stage'] = 'boot_and_probe_image'
            api = docker.container(image['Id'], '--env-file', str(env_file),
                '--env', 'FOCUS_READONLY_ROLLBACK_APPROVED=true', '--read-only',
                '--tmpfs', '/tmp:rw,nosuid,size=16m', '--cap-drop=ALL',
                '--security-opt=no-new-privileges', '--memory=512m', '--cpus=1', '--pids-limit=64')
            api_config = json.loads(docker.run('container', 'inspect', api))[0]
            assert not api_config['Mounts'] or all(m['Type'] == 'tmpfs' for m in api_config['Mounts'])
            assert not api_config['HostConfig']['PortBindings']
            value = json.loads(docker.run('exec', '-i', api, 'python', '-', 'probe', stdin=probe))
            report['checks'].extend(value['checks'])
            docker.run('stop', '--time', '5', api)
            log = docker.run('logs', api, combined=True)
            assert not any(value in log for value in ('Traceback', 'postgresql://', 'issue14-owner',
                                                      'issue14-rep', 'DATABASE_URL='))
            report['checks'].append('runtime_logs_without_traceback_connection_or_session_values')
            assert docker.snapshot(pg) == before
            report['checks'].append('all_21_table_counts_sha256_unchanged')
            # Negative cases run the same image/default CMD; never touch a host or production DB.
            for name, revision in [('approval_missing', '007'), ('schema_004_rejected', '004'),
                                   ('schema_006_rejected', '006')]:
                report['stage'] = name
                docker.sql(pg, "UPDATE alembic_version SET version_num='" + revision + "'")
                checkpoint = docker.snapshot(pg)
                args = ['--env-file', str(env_file), '--read-only', '--tmpfs', '/tmp:rw,nosuid,size=16m',
                        '--cap-drop=ALL', '--security-opt=no-new-privileges', '--memory=512m',
                        '--cpus=1', '--pids-limit=64']
                if name != 'approval_missing':
                    args += ['--env', 'FOCUS_READONLY_ROLLBACK_APPROVED=true']
                denied = docker.container(image['Id'], *args)
                assert docker.run('wait', denied) == '1'
                # Only the fixed refusal message, no secrets/traceback or raw logs as artifact.
                assert docker.run('logs', denied, combined=True) == 'BLOCKED: readonly rollback startup refused'
                assert docker.snapshot(pg) == checkpoint
                report['checks'].append(name)
            report['sanitized_refusal_log'] = 'BLOCKED: readonly rollback startup refused (3 cases)'
            docker.sql(pg, "UPDATE alembic_version SET version_num='007'")
            assert docker.snapshot(pg) == before
            report['fingerprints_before'] = before
            report['fingerprints_after'] = docker.snapshot(pg)
        report['container_runtime'] = 'PASS'
        report['stage'] = 'complete'
    except Exception:
        report['failure'] = 'CONTAINER_SMOKE_FAILED_NO_RAW_EXCEPTION_LOGGED'
    finally:
        try:
            docker.cleanup()
            report['cleanup'] = 'PASS'
        except Exception:
            report['cleanup'] = 'BLOCKED'
            report['container_runtime'] = 'BLOCKED'
        results.parent.mkdir(parents=True, exist_ok=True)
        results.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if not k.startswith('fingerprints')}))
    return 0 if report['container_runtime'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Already-built local image; no pull/push')
    parser.add_argument('--results', required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(execute(args.image, args.results))
