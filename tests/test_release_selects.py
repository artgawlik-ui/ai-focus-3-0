"""Zapytania sprawdzane tylko na syntetycznym PostgreSQL; brak cleanup salonu."""
import pytest,psycopg
from backend.db import engine
from tests.test_api import clean,client,add
from scripts.release_selects import TABLES,queries,render_sql


def connect():
    assert engine.url.host in ('localhost','127.0.0.1') and engine.url.database=='focus3_test'
    return psycopg.connect(engine.url.render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://'),autocommit=True)


def test_minimal_queries_readonly_accounts_and_all_table_hashes():
    owner=client();rep=client('rep1');add(owner,name='Synthetic SELECT validation')
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS public.alembic_version (version_num varchar(32) PRIMARY KEY)')
        db.execute("INSERT INTO public.alembic_version VALUES ('004') ON CONFLICT DO NOTHING")
    assert owner.post('/api/users/rep1/deactivate').status_code==200
    params={'owner_user_id':'manager','technical_user_id':'rep1'}
    with connect() as db:
        db.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        try:
            db.execute("SET LOCAL TIME ZONE 'UTC'")
            db.execute("SET LOCAL statement_timeout='5s'")
            q=queries();base=db.execute(q['baseline']).fetchone()
            assert base==(True,True,17,['004'],17,True,True)
            assert db.execute(q['accounts'],params).fetchone()==(True,True,True,0,0)
            first=db.execute(q['fingerprints']).fetchall();second=db.execute(q['fingerprints']).fetchall()
            assert first==second and [r[0] for r in first]==list(TABLES)
            assert len(first)==17 and all(len(r[2])==64 for r in first)
            assert all(value==0 for value in db.execute(q['worker']).fetchone())
            assert db.execute(q['accounts'],{'owner_user_id':None,'technical_user_id':None}).fetchone()[:3]==(False,False,False)
            bad={'owner_user_id':'missing','technical_user_id':'manager'}
            assert db.execute(q['accounts'],bad).fetchone()[1:3]==(False,False)
        finally:db.execute('ROLLBACK')


def test_query_bundle_is_static_select_only_with_private_parameters():
    q=queries();assert len(q)==4
    assert all(value.lstrip().startswith('SELECT') and ';' not in value for value in q.values())
    for forbidden in ('DELETE ','UPDATE ','INSERT ','CREATE ','DROP ','COPY ','COMMIT'):
        assert all(forbidden not in value.upper() for value in q.values())
    assert '%(owner_user_id)s' in q['accounts'] and '%(technical_user_id)s' in q['accounts']
    assert render_sql().rstrip().endswith('ROLLBACK;')
    rendered=render_sql(psql=True)
    assert '%(owner_user_id)s' not in rendered and " :'owner_user_id'" in rendered
    assert rendered.count('\\prompt ')==2 and rendered.rstrip().endswith('ROLLBACK;')


def test_retention_candidates_use_timestamp_comparison_on_boundary_day():
    from datetime import datetime,timedelta,timezone
    from backend.db import Session
    from backend.meta_models import MetaWebhookInbox
    now=datetime.now(timezone.utc)
    with Session() as db:
        for name,delta in [('old',timedelta(days=7,hours=1)),('new',timedelta(days=6,hours=23))]:
            db.add(MetaWebhookInbox(id=name,dedup_key=name,account_id='synthetic',payload_ciphertext='synthetic',status='done',processed_at=(now-delta).isoformat()))
        db.commit()
    with connect() as db:
        db.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        try:
            row=db.execute(queries()['worker']).fetchone()
            assert row[4]==1 and row[5]==0 and row[-1]==0
        finally:db.execute('ROLLBACK')
