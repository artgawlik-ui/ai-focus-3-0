"""Opt-in API-only emergency profile for schema007. No migrations or workers."""
import json
import os
import re
import sys
from sqlalchemy.engine import make_url

OPTIONS = '-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000'
OFF = ('META_ENABLED', 'META_OAUTH_ENABLED', 'META_WEBHOOK_VERIFY_ENABLED',
       'META_INGEST_ENABLED', 'META_CRM_HISTORY_ENABLED', 'META_DIAGNOSTICS_ENABLED',
       'META_DM_TRANSPORT_ENABLED', 'GOOGLE_SCHEMA_ENABLED', 'GOOGLE_CALENDAR_ENABLED',
       'GOOGLE_CALENDAR_WRITE_ENABLED', 'FOCUS_CALENDAR_SCHEMA_ENABLED',
       'FOCUS_CALENDAR_ENABLED', 'FOCUS_DIAGNOSTICS_ENABLED', 'AI_PAID_PROCESSING_APPROVED',
       'OFFSITE_BACKUP_ENABLED', 'AGENT_V2_ENABLED')
READ_PATHS = frozenset(('/api/health', '/api/auth/me', '/api/salons',
                        '/api/appointments', '/api/dashboard'))


class Blocked(RuntimeError):
    pass


def profile(environment):
    if environment.get('FOCUS_READONLY_ROLLBACK_APPROVED') != 'true':
        raise Blocked('ROLLBACK_APPROVAL_REQUIRED')
    try:
        url = make_url(environment.get('DATABASE_URL', ''))
        if url.drivername not in ('postgres', 'postgresql', 'postgresql+psycopg') or not url.database:
            raise ValueError()
        # Preserve TLS settings; replace all caller-supplied options, including read-write overrides.
        url = url.set(drivername='postgresql+psycopg').update_query_dict({'options': OPTIONS})
        result = {name: 'false' for name in OFF}
        result.update(DATABASE_URL=url.render_as_string(hide_password=False), WORKER_PAUSED='true')
        return result
    except Exception:
        raise Blocked('ROLLBACK_DATABASE_INVALID') from None


def allowed(method, path):
    return method in ('GET', 'HEAD') and (path in READ_PATHS or
        re.fullmatch(r'/api/salons/[A-Za-z0-9_-]{1,36}(?:/activities)?', path) is not None)


class ReadOnlyAPI:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = [(b'cache-control', b'no-store'), (b'x-focus-mode', b'rollback-readonly'),
                   (b'x-content-type-options', b'nosniff'), (b'x-frame-options', b'DENY')]
        if scope['path'] == '/' and scope['method'] in ('GET', 'HEAD'):
            body = json.dumps({'mode': 'rollback-readonly', 'writes': False,
                               'login_available': False, 'worker': False}).encode()
            await send({'type': 'http.response.start', 'status': 200,
                        'headers': headers + [(b'content-type', b'application/json')]})
            return await send({'type': 'http.response.body', 'body': body})
        if not allowed(scope['method'], scope['path']):
            body = json.dumps({'detail': 'Awaryjny tryb tylko do odczytu; operacja niedostępna.'}).encode()
            await send({'type': 'http.response.start', 'status': 503,
                        'headers': headers + [(b'content-type', b'application/json')]})
            return await send({'type': 'http.response.body', 'body': body})
        started = False
        async def guarded_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
                original = [(key, value) for key, value in message.get('headers', [])
                            if key.lower() not in {name for name, _ in headers}]
                message = {**message, 'headers': original + headers}
            await send(message)
        try:
            return await self.app(scope, receive, guarded_send)
        except Exception:
            # Driver exceptions may contain connection metadata; never propagate them to logs.
            if not started:
                await send({'type': 'http.response.start', 'status': 503, 'headers': headers})
                await send({'type': 'http.response.body', 'body': b'Rollback read unavailable'})


def create_app():
    # Refuse reuse of a previously initialized writable engine in this process.
    if 'backend.db' in sys.modules:
        raise Blocked('ROLLBACK_REQUIRES_FRESH_PROCESS')
    os.environ.update(profile(os.environ))
    try:
        from sqlalchemy import text
        from backend.db import engine
        from scripts.release_selects import TABLES
        expected = set(TABLES) | {'focus_contact_policies', 'focus_work_settings',
                                  'focus_tasks', 'focus_notifications'}
        with engine.connect() as db:
            if db.scalar(text("SELECT current_setting('transaction_read_only')")) != 'on':
                raise ValueError()
            if db.scalar(text("SELECT current_setting('server_version_num')::integer/10000")) != 17:
                raise ValueError()
            if list(db.scalars(text('SELECT version_num FROM public.alembic_version'))) != ['007']:
                raise ValueError()
            names = set(db.scalars(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")))
            if names != expected:
                raise ValueError()
        from backend.main import app
        return ReadOnlyAPI(app)
    except Exception:
        raise Blocked('ROLLBACK_SCHEMA_OR_CONNECTION_REJECTED') from None


def main():
    try:
        application = create_app()
        import uvicorn
        uvicorn.run(application, host='0.0.0.0', port=int(os.getenv('PORT', '8000')),
                    access_log=False, log_level='warning', proxy_headers=True,
                    forwarded_allow_ips=os.getenv('TRUSTED_PROXY_IPS', '127.0.0.1'))
        return 0
    except Exception:
        print('BLOCKED: readonly rollback startup refused', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
