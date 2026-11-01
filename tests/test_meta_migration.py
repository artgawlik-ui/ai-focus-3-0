"""Migration/rollback uses a newly created LOCAL database, never production."""
import os,subprocess,sys,uuid,hashlib,json
import psycopg
from sqlalchemy.engine import make_url

def test_004_empty_upgrade_repeat_and_preserving_rollback():
    source=make_url(os.environ['DATABASE_URL'])
    assert source.host in ('localhost','127.0.0.1','postgres') and source.database=='focus3_test'
    name='focus3_migration_'+uuid.uuid4().hex[:10]
    admin=source.set(database='postgres').render_as_string(hide_password=False)
    target=source.set(database=name).render_as_string(hide_password=False)
    with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
    env={**os.environ,'DATABASE_URL':target,'APP_ENV':'test'}
    def alembic(*args):
        # Capture; no provider credentials/OAuth codes exist in this subprocess.
        result=subprocess.run([sys.executable,'-m','alembic',*args],env=env,capture_output=True)
        assert result.returncode==0,'Isolated migration command failed'
    try:
        alembic('upgrade','003')
        with psycopg.connect(target) as db:
            db.execute("INSERT INTO users (id,email,name,password_hash,role,active) VALUES ('fixture','fixture@invalid.test','Fixture','not-a-password','manager',1)")
        def fingerprint():
            with psycopg.connect(target) as db:
                tables=[r[0] for r in db.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT IN ('alembic_version','meta_webhook_inbox','meta_refresh_states') ORDER BY tablename")]
                result={}
                from psycopg import sql
                for table in tables:
                    rows=db.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text').format(sql.Identifier(table))).fetchall()
                    result[table]=(len(rows),hashlib.sha256(json.dumps(rows).encode()).hexdigest())
                return result
        before=fingerprint()
        alembic('upgrade','head');alembic('upgrade','head')
        assert fingerprint()==before
        with psycopg.connect(target) as db:
            db.execute("INSERT INTO meta_webhook_inbox (id,dedup_key,account_id,payload_ciphertext,status,attempts,next_attempt_at,lease_until,lease_token,created_at,updated_at,processed_at,last_error,dead_letter) VALUES ('fixture','fixture','fixture','encrypted-fixture','pending',0,'','','','','','','',0)")
        alembic('downgrade','003');alembic('upgrade','head')
        assert fingerprint()==before
        with psycopg.connect(target) as db:
            assert db.execute('SELECT COUNT(*) FROM meta_webhook_inbox').fetchone()[0]==1
        alembic('check')
    finally:
        with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name+' WITH (FORCE)')
