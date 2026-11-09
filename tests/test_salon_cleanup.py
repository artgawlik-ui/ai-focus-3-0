"""Wyłącznie syntetyczny PostgreSQL; brak połączeń z produkcją."""
import json,uuid,pytest,psycopg
from sqlalchemy import select
from tests.test_api import clean,client,add
from backend.db import Session,engine,Activity,Appointment,Job
from scripts.salon_cleanup import inspection_sql,build_delete_sql,build_restore_sql,CleanupError,TABLES

pytestmark=pytest.mark.skipif(engine.dialect.name!='postgresql',reason='Transakcyjny plan wymaga PostgreSQL')

def connect():
    return psycopg.connect(str(engine.url.render_as_string(hide_password=False)).replace('postgresql+psycopg://','postgresql://'))


def prepare():
    c=client();target=add(c,name='Synthetic cleanup');other=add(c,name='Synthetic retained')
    with Session() as db:
        db.add(Appointment(id=str(uuid.uuid4()),salon_id=target['id'],user_id='manager',starts_at='2030-01-01T12:00:00Z',ends_at='2030-01-01T12:20:00Z',status='proposed',notes='fixture'))
        db.add(Job(id=str(uuid.uuid4()),salon_id=target['id'],user_id='manager',status='completed'));db.commit()
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS alembic_version (version_num varchar(32) PRIMARY KEY)');db.execute('DELETE FROM alembic_version');db.execute("INSERT INTO alembic_version VALUES ('004')");db.commit()
        plan=db.execute(inspection_sql(target['id'])).fetchone()[0]
        rows={table:db.execute('SELECT to_jsonb(t) FROM '+table+' t WHERE '+('id' if table=='salons' else 'salon_id')+'=%s',(target['id'],)).fetchall() for table in TABLES}
    plan.update(original_target_id=target['id'],owner_confirmed_original_test=True,fresh_backup_verified=True,backup_sha256='a'*64)
    return plan,{k:[x[0] for x in v] for k,v in rows.items()},other


def run_sql(script):
    with connect() as db:db.autocommit=True;db.execute(script)


def test_default_rollback_and_scoped_undo_after_synthetic_commit():
    plan,rows,other=prepare();script=build_delete_sql(plan,'focus3_test')
    assert script.rstrip().endswith('ROLLBACK;') and 'CASCADE' not in script
    run_sql(script)
    with connect() as db:assert db.execute('SELECT count(*) FROM salons').fetchone()[0]==2
    # Wyłącznie syntetyczna baza: potwierdzamy też naprawę po COMMIT.
    run_sql(script.rsplit('ROLLBACK;',1)[0]+'COMMIT;')
    with connect() as db:assert db.execute('SELECT id FROM salons').fetchone()[0]==other['id']
    undo=build_restore_sql(plan,rows,'focus3_test');run_sql(undo)
    with connect() as db:assert db.execute('SELECT count(*) FROM salons').fetchone()[0]==1
    run_sql(undo.rsplit('ROLLBACK;',1)[0]+'COMMIT;')
    with connect() as db:
        after=db.execute(inspection_sql(plan['target_id'])).fetchone()[0]
        assert after['tables']==plan['tables']
        assert db.execute('SELECT count(*) FROM salons WHERE id=%s',(other['id'],)).fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM users').fetchone()[0]==3


@pytest.mark.parametrize('change',['salon','child','new_child','meta_link','running_job'])
def test_changed_scope_is_rejected(change):
    plan,rows,other=prepare()
    with connect() as db:
        if change=='salon':db.execute("UPDATE salons SET notes='changed' WHERE id=%s",(plan['target_id'],))
        if change=='child':db.execute("UPDATE activities SET body='changed' WHERE salon_id=%s",(plan['target_id'],))
        if change=='new_child':db.execute("INSERT INTO activities (id,salon_id,user_id,kind,body,created_at) VALUES (%s,%s,'manager','note','fixture','2030')",(str(uuid.uuid4()),plan['target_id']))
        if change=='running_job':db.execute("UPDATE jobs SET status='running' WHERE salon_id=%s",(plan['target_id'],))
        if change=='meta_link':db.execute("INSERT INTO meta_conversations (id,account_id,peer_id,salon_id,last_inbound_at,opted_out,created_at) VALUES (%s,'fixture','fixture',%s,'',0,'2030')",(str(uuid.uuid4()),plan['target_id']))
        db.commit()
    with pytest.raises(psycopg.Error):run_sql(build_delete_sql(plan,'focus3_test'))
    with connect() as db:assert db.execute('SELECT count(*) FROM salons').fetchone()[0]==2


def test_new_cascading_foreign_key_is_rejected():
    plan,rows,other=prepare()
    try:
        with connect() as db:db.execute('CREATE TABLE cleanup_extra (id text PRIMARY KEY, salon_id varchar(36) REFERENCES salons(id) ON DELETE CASCADE)');db.commit()
        with pytest.raises(psycopg.Error):run_sql(build_delete_sql(plan,'focus3_test'))
        with connect() as db:assert db.execute('SELECT count(*) FROM salons').fetchone()[0]==2
    finally:
        with connect() as db:db.execute('DROP TABLE IF EXISTS cleanup_extra');db.commit()


def test_unconfirmed_identity_and_restore_collision_are_rejected():
    plan,rows,other=prepare();bad={**plan,'original_target_id':str(uuid.uuid4())}
    with pytest.raises(CleanupError):build_delete_sql(bad)
    with pytest.raises(CleanupError):build_delete_sql({**plan,'fresh_backup_verified':False})
    with pytest.raises(CleanupError):build_delete_sql(plan,'focus2')
    with pytest.raises(psycopg.Error):run_sql(build_restore_sql(plan,rows,'focus3_test'))


def test_encrypted_backup_and_undo_are_authenticated():
    from scripts.cleanup_backup import encrypt,decrypt
    from cryptography.exceptions import InvalidTag
    phrase='synthetic-backup-key-not-used-in-production'
    payload=b'fixture archive data'
    cipher=encrypt(payload,phrase,'archive')
    assert payload not in cipher and decrypt(cipher,phrase,'archive')==payload
    for key,kind,data in ((phrase,'undo',cipher),('different-synthetic-backup-passphrase','archive',cipher),(phrase,'archive',cipher[:-1]+bytes([cipher[-1]^1]))):
        with pytest.raises(InvalidTag):decrypt(data,key,kind)


def test_custom_trigger_is_rejected_before_trigger_execution():
    plan,rows,other=prepare()
    try:
        with connect() as db:
            db.execute("CREATE FUNCTION cleanup_test_trigger() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'trigger should not run'; END $$")
            db.execute('CREATE TRIGGER cleanup_test_before BEFORE DELETE ON activities FOR EACH ROW EXECUTE FUNCTION cleanup_test_trigger()');db.commit()
        with pytest.raises(psycopg.Error) as error:run_sql(build_delete_sql(plan,'focus3_test'))
        assert error.value.diag.message_primary=='Custom triggers or rules'
    finally:
        with connect() as db:db.execute('DROP TRIGGER IF EXISTS cleanup_test_before ON activities');db.execute('DROP FUNCTION IF EXISTS cleanup_test_trigger()');db.commit()


def test_even_reviewed_schema_cannot_enable_cascading_unknown_children():
    from scripts.salon_cleanup import SCHEMA_SQL
    plan,rows,other=prepare()
    try:
        with connect() as db:
            db.execute('CREATE TABLE cleanup_extra (id text PRIMARY KEY, salon_id varchar(36) REFERENCES salons(id) ON DELETE CASCADE)')
            db.execute("INSERT INTO cleanup_extra VALUES ('retained',%s)",(plan['target_id'],));db.commit()
            plan['schema_sha256']=db.execute('SELECT '+SCHEMA_SQL).fetchone()[0]
        with pytest.raises(psycopg.Error) as error:run_sql(build_delete_sql(plan,'focus3_test'))
        assert error.value.diag.message_primary=='Unexpected incoming foreign key'
        with connect() as db:assert db.execute('SELECT count(*) FROM cleanup_extra').fetchone()[0]==1
    finally:
        with connect() as db:db.execute('DROP TABLE IF EXISTS cleanup_extra');db.commit()
