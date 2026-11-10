"""Synthetic-only code sent over stdin to the image; never included in the image."""
import asyncio
import json
import os
from pathlib import Path
import socket
import sys
import time


def seed():
    from backend.db import User, Salon, LoginSession, Activity, Appointment, Job, Session
    from backend.native_models import Task
    from backend.meta_models import MetaWebhookInbox
    from backend.security import digest
    with Session() as db:
        for name, role, active in [('owner', 'manager', 1), ('rep', 'sales', 1),
                                   ('disabled', 'manager', 0)]:
            db.add(User(id='fixture-' + name, email=name + '@focus.invalid', name='Synthetic',
                        password_hash='not-a-login-hash', role=role, active=active))
        db.flush()
        for name in ('owner', 'rep', 'disabled', 'expired'):
            db.add(LoginSession(token_hash=digest('issue14-' + name),
                user_id='fixture-owner' if name == 'expired' else 'fixture-' + name,
                csrf='synthetic-unused', expires=('2000' if name == 'expired' else '2999') +
                '-01-01T00:00:00+00:00'))
        for i in range(3):
            sid = 'fixture-salon-' + str(i)
            db.add(Salon(id=sid, owner_id='fixture-rep' if i == 0 else 'fixture-owner',
                         name='[SYNTHETIC] Salon ' + str(i), city='Synthetic', dedup_key=sid))
            db.flush()
            db.add(Activity(id='fixture-activity-' + str(i), salon_id=sid, user_id='fixture-owner',
                            kind='call', body='Synthetic contact'))
        db.add(Appointment(id='fixture-visit', salon_id='fixture-salon-0', user_id='fixture-rep',
                           starts_at='2999-01-01T10:00:00+00:00', ends_at='2999-01-01T10:20:00+00:00'))
        db.add(Job(id='fixture-queued', salon_id='fixture-salon-0', user_id='fixture-owner'))
        db.add(Task(id='fixture-due', salon_id='fixture-salon-0', assignee_id='fixture-owner',
                    title='Synthetic overdue task', due_at='2000-01-01T00:00:00+00:00'))
        db.add(MetaWebhookInbox(id='fixture-expired', dedup_key='fixture-expired',
            account_id='fixture-account', payload_ciphertext='synthetic-never-decrypt',
            status='done', processed_at='2000-01-01T00:00:00+00:00'))
        db.commit()
    return ['synthetic_seed']


def probe():
    import httpx
    checks = []
    base = 'http://127.0.0.1:8000'
    end = time.monotonic() + 15
    with httpx.Client(base_url=base, timeout=2, trust_env=False) as client:
        while True:
            try:
                if client.get('/api/health').status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            assert time.monotonic() < end, 'readiness'
            time.sleep(.1)
        checks.append('image_default_cmd_ready_007')
        root = client.get('/')
        assert root.status_code == 200 and root.json() == {
            'mode': 'rollback-readonly', 'writes': False, 'login_available': False, 'worker': False}
        assert root.headers['cache-control'] == 'no-store'
        for token in (None, 'disabled', 'expired', 'unknown'):
            headers = {} if token is None else {'Cookie': 'focus_session=issue14-' + token}
            assert client.get('/api/salons', headers=headers).status_code == 401
        owner = {'Cookie': 'focus_session=issue14-owner'}
        rep = {'Cookie': 'focus_session=issue14-rep'}
        for headers, total in [(owner, 3), (rep, 1)]:
            response = client.get('/api/salons', headers=headers)
            assert response.status_code == 200 and response.json()['total'] == total
            assert response.headers['cache-control'] == 'no-store'
            assert response.headers['x-focus-mode'] == 'rollback-readonly'
        assert client.get('/api/salons/fixture-salon-1', headers=rep).status_code == 404
        for path in ('/api/auth/me', '/api/salons/fixture-salon-0',
                     '/api/salons/fixture-salon-0/activities', '/api/appointments', '/api/dashboard'):
            assert client.get(path, headers=owner).status_code == 200
        checks.extend(['existing_session_rbac', 'disabled_expired_unauthenticated_denied',
                       'allowed_reads_no_store'])
        for method, path in [('POST', '/api/auth/login'), ('POST', '/api/auth/logout'),
                             ('POST', '/api/salons'), ('PATCH', '/api/salons/fixture-salon-0'),
                             ('DELETE', '/api/salons/fixture-salon-0'),
                             ('PATCH', '/api/appointments/fixture-visit'),
                             ('POST', '/api/agent/jobs'), ('GET', '/api/focus/tasks'),
                             ('GET', '/api/export.xlsx'), ('GET', '/docs'),
                             ('GET', '/api/meta/oauth/callback'), ('POST', '/api/meta/webhook'),
                             ('GET', '/api/google/oauth/callback'), ('GET', '/api/discovery/places')]:
            response = client.request(method, path, headers=owner)
            assert response.status_code == 503 and response.headers['cache-control'] == 'no-store'
        checks.append('writes_login_integrations_denied')
    # Exercise the actual TCP server: an upgrade must never become a WebSocket.
    # Uvicorn's minimal image can lack a WS implementation; record refusal, not a wire close code.
    with socket.create_connection(('127.0.0.1', 8000), timeout=2) as connection:
        connection.sendall(b'GET /api/salons HTTP/1.1\r\nHost: localhost\r\n'
            b'Connection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\n'
            b'Sec-WebSocket-Key: Zml4dHVyZS1vbmx5LWtleQ==\r\n\r\n')
        first = connection.recv(4096).split(b'\r\n', 1)[0]
        assert first.startswith(b'HTTP/1.1 ') and first.split()[1] != b'101'
    checks.append('wire_websocket_upgrade_refused')
    # A second fresh process in the exact image also verifies ASGI close and DB/session guards.
    from scripts.rollback_readonly import create_app, OFF
    app = create_app()
    assert all(os.environ[name] == 'false' for name in OFF)
    assert os.environ['WORKER_PAUSED'] == 'true'
    messages = []
    async def send(message):
        messages.append(message)
    asyncio.run(app({'type': 'websocket', 'path': '/api/salons'}, None, send))
    assert messages == [{'type': 'websocket.close', 'code': 1008}]
    checks.append('image_asgi_websocket_1008')
    from backend.db import engine
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    with engine.connect() as db:
        assert db.scalar(text("SELECT current_setting('transaction_read_only')")) == 'on'
    try:
        with engine.begin() as db:
            db.execute(text('UPDATE public.users SET active=active'))
    except DBAPIError as error:
        assert error.orig.sqlstate == '25006'
    else:
        raise AssertionError('database_write_allowed')
    checks.append('image_database_write_denied_25006')
    assert os.geteuid() == 10001
    assert Path('/proc/1/cmdline').read_bytes().split(b'\0')[:3] == [
        b'python', b'-m', b'scripts.rollback_readonly']
    # Only PID1 and this probe; no supervisor, migration, bootstrap or worker process.
    processes = [p for p in Path('/proc').glob('[0-9]*/cmdline') if p.read_bytes()]
    assert len(processes) == 2
    assert 'backend.worker' not in sys.modules and 'scripts.bootstrap' not in sys.modules
    for path in ('migrations', 'scripts/bootstrap.py', 'scripts/supervise.py',
                 'scripts/start.sh', 'scripts/offsite_backup.py'):
        assert not Path('/app', path).exists()
    checks.extend(['nonroot_default_entrypoint_no_children', 'no_migration_bootstrap_worker',
                   'integrations_forced_off'])
    return checks


if __name__ == '__main__':
    try:
        result = seed() if sys.argv[1:] == ['seed'] else probe()
        print(json.dumps({'checks': result}))
    except Exception:
        # No traceback, HTTP body, cookies, connection URL or exception message in CI logs.
        print('Synthetic image probe failed', file=sys.stderr)
        raise SystemExit(1)
