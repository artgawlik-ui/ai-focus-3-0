"""Rzeczywisty pg_dump/pg_restore, wyłącznie syntetyczny lokalny PostgreSQL."""
import os, uuid
from pathlib import Path
import psycopg
from psycopg import sql
from scripts.backup import backup, restore, fingerprint
from tests.test_salon_cleanup import clean, prepare
from backend.db import engine


def test_encrypted_backup_restore_all_tables_and_source_unchanged(tmp_path, monkeypatch):
    source=engine.url.render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    assert engine.url.host in ('localhost','127.0.0.1') and engine.url.database=='focus3_test'
    prepare()
    before=fingerprint(source, include_metadata=True)
    assert len(before)==17 and before['salons']['count']==2
    name='focus3_synthetic_'+uuid.uuid4().hex[:12]
    target=engine.url.set(database=name).render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    admin=engine.url.set(database='postgres').render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    monkeypatch.setenv('PATH',str(Path('.tools').resolve())+os.pathsep+os.environ['PATH'])
    monkeypatch.setenv('BACKUP_PASSPHRASE',uuid.uuid4().hex+uuid.uuid4().hex)
    monkeypatch.setenv('RESTORE_DATABASE_URL',target)
    archive=tmp_path/'synthetic.enc'
    with psycopg.connect(admin,autocommit=True) as db:
        db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    try:
        backup(archive,url=source)
        assert archive.stat().st_mode & 0o777==0o600
        assert archive.read_bytes().startswith(b'FOCUS3B1')
        restore(archive)
        assert fingerprint(target,include_metadata=True)==before
        assert fingerprint(source,include_metadata=True)==before
    finally:
        with psycopg.connect(admin,autocommit=True) as db:
            db.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        archive.unlink(missing_ok=True)
