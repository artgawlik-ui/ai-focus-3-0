"""Świeża syntetyczna baza lokalna -> eksport -> restore w kontenerze bez sieci."""
import argparse, hashlib, json, os, subprocess, sys, tarfile, tempfile, uuid
from pathlib import Path
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from scripts.backup import pg_env


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if os.getenv('APP_ENV')=='production':raise SystemExit('Tryb produkcyjny zabroniony')
    source=make_url(os.environ['DATABASE_URL'])
    if source.host not in ('localhost','127.0.0.1') or source.database!='focus3_test':
        raise SystemExit('Wymagana lokalna baza testowa')
    name='focus3_synthetic_'+uuid.uuid4().hex[:12]
    url=source.set(database=name).render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    admin=source.set(database='postgres').render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    env={**os.environ,'DATABASE_URL':url,'APP_ENV':'test','AI_PAID_PROCESSING_APPROVED':'false','OFFSITE_BACKUP_ENABLED':'false'}
    for flag in ('ENABLED','OAUTH_ENABLED','WEBHOOK_VERIFY_ENABLED','INGEST_ENABLED','CRM_HISTORY_ENABLED','DIAGNOSTICS_ENABLED','DM_TRANSPORT_ENABLED'):
        env['META_'+flag]='false'
    def run(command, child_env=env):
        result=subprocess.run(command,env=child_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180)
        if result.returncode:raise RuntimeError('Lokalny etap nieudany; odpowiedzi i dane ukryte')
    with psycopg.connect(admin,autocommit=True) as db:
        db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    try:
        run([sys.executable,'-m','alembic','upgrade','head'])
        run([sys.executable,'-c',"from backend.db import Session,User,Salon; from backend.security import ph; db=Session(); db.add(User(id='synthetic-owner',email='owner@example.invalid',name='Synthetic owner',password_hash=ph.hash('SyntheticFixtureOnly42!'),role='manager',active=1)); db.commit(); db.add(Salon(id='synthetic-salon',name='Synthetic salon',city='Synthetic city',owner_id='synthetic-owner',dedup_key='synthetic-local-only')); db.commit(); db.close()"])
        with tempfile.TemporaryDirectory(prefix='focus3-synthetic-export-') as temp:
            root=Path(temp);dump=root/'dump'
            run([str(Path('.tools/pg_dump').resolve()),'--format=directory','--no-owner','--no-acl','--file='+str(dump)],pg_env(url))
            archive=root/'synthetic.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:tar.add(dump,arcname='dump')
            digest=hashlib.sha256(archive.read_bytes()).hexdigest()
            run([sys.executable,'-m','scripts.isolated_export_restore','--archive',str(archive),'--sha256',digest,'--output',args.output,'--synthetic-source-name',name])
            result=json.loads(Path(args.output).read_text())
            if result['status']!='RESTORE_AND_EXPORT_POINT_INTEGRITY_PASS' or not result['synthetic_source']:raise RuntimeError('Brak potwierdzenia restore')
    finally:
        with psycopg.connect(admin,autocommit=True) as db:
            db.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
    print('Syntetyczny restore bez sieci: PASS; baza źródłowa i pliki tymczasowe usunięte')

if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Syntetyczny restore: BLOCKED; dane i wyjątki ukryte')
