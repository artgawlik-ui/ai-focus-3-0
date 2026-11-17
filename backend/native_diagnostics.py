"""Manager-only read projections. Never activate a worker or modify a queue."""
import json
import os
from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from backend.native_planning import router, schema_enabled, enabled
from backend.security import manager, database
from backend import worker_control
from backend.native_notifications import TASK_SOURCE, VISIT_SOURCE


def diagnostics_enabled():
    return os.getenv('FOCUS_DIAGNOSTICS_ENABLED', '').strip().lower() == 'true'


def worker_snapshot(instant):
    result = {'state': 'unknown', 'signal': 'unknown', 'age_seconds': None,
              'pause_requested': worker_control.paused(), 'native_last_success_at': None}
    try:
        with worker_control.STATUS_FILE.open(encoding='utf-8') as source:
            raw = source.read(4097)
        if len(raw) > 4096:
            return result
        status = json.loads(raw)
        state = status.get('state')
        at = datetime.fromisoformat(status['at'])
        if state not in ('running', 'idle', 'paused', 'degraded', 'stopped') or at.tzinfo is None:
            return result
        age = (instant - at).total_seconds()
        if age < -5:
            return result
        result.update(state=state, signal='fresh' if age <= 30 else 'stale',
                      age_seconds=max(0, int(age)))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    return result


def reminder_backlog(db, instant):
    source = "SELECT 'task' AS kind,l.* FROM (" + TASK_SOURCE + ") l UNION ALL SELECT 'visit' AS kind,l.* FROM (" + VISIT_SOURCE + ') l'
    row = db.execute(text('WITH live AS (' + source + ''') SELECT
        count(*) FILTER (WHERE l.kind='task') AS tasks,
        count(*) FILTER (WHERE l.kind='visit') AS visits,
        min(CAST(l.due_at AS timestamptz)) AS oldest_due_at
        FROM live l WHERE NOT EXISTS (SELECT 1 FROM focus_notifications n
        WHERE n.key=l.key AND n.user_id=l.user_id)
        '''), {'now': instant.isoformat()}).mappings().one()
    oldest = row['oldest_due_at']
    return {'tasks': row['tasks'], 'visits': row['visits'],
            'oldest_due_at': oldest.isoformat() if oldest else None,
            'oldest_overdue_seconds': max(0, int((instant-oldest).total_seconds())) if oldest else None}


@router.get('/diagnostics')
def diagnostics(user=Depends(manager), db=Depends(database)):
    if not diagnostics_enabled():
        raise HTTPException(404, 'Podgląd diagnostyki wyłączony')
    instant = datetime.now(timezone.utc)
    row = db.execute(text('''SELECT
        count(*) FILTER(WHERE status='queued') AS queued,
        count(*) FILTER(WHERE status='running') AS running,
        count(*) FILTER(WHERE status='failed') AS failed,
        count(*) FILTER(WHERE status='completed') AS completed,
        min(CASE WHEN pg_input_is_valid(created_at,'timestamp with time zone') THEN CAST(created_at AS timestamptz) END) FILTER(WHERE status='queued') AS oldest
        FROM jobs''')).mappings().one()
    oldest = row['oldest']
    jobs = {key: row[key] for key in ('queued', 'running', 'failed', 'completed')}
    jobs['oldest_queued_age_seconds'] = max(0, int((instant-oldest).total_seconds())) if oldest else None
    native = {'available': False, 'reason': 'schema_disabled', 'pending_reminders': None}
    if schema_enabled():
        try:
            native = {'available': True, 'reason': None, 'pending_reminders': reminder_backlog(db, instant)}
        except SQLAlchemyError:
            db.rollback()
            native['reason'] = 'schema_or_query_unavailable'
    return {'read_only': True, 'sampled_at': instant.isoformat(), 'worker': worker_snapshot(instant),
            'agent_jobs': jobs, 'native': native,
            'flags': {'schema_enabled': schema_enabled(), 'runtime_enabled': enabled()},
            'limitations': ['Heartbeat does not confirm successful native processing.',
                            'Reminder age measures overdue time, not queue residence time.'],
            'external_messages': False, 'retention_execution_available': False}
