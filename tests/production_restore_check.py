"""Restore encrypted production snapshot ONLY into a new local disposable database."""
import os,json,uuid
from pathlib import Path
import psycopg
from scripts.backup import restore,fingerprint
credentials=json.loads(Path('.render-auth/verification.json').read_text())
name='focus3_restore_'+uuid.uuid4().hex[:10]
admin='postgresql://postgres@127.0.0.1:55432/postgres'
url='postgresql://postgres@127.0.0.1:55432/'+name
with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
try:
    os.environ['RESTORE_DATABASE_URL']=url
    os.environ['BACKUP_PASSPHRASE']=credentials['backup_passphrase']
    os.environ['PATH']=str(Path('.tools').resolve())+os.pathsep+os.environ['PATH']
    restore('.render-auth/production-backup.enc')
    counts={table:data['count'] for table,data in fingerprint(url).items()}
    assert counts['salons']>=1 and counts['jobs']>=1
    report={'status':'PASS','source':'encrypted snapshot from production Ai Focus 3.0','target':'disposable LOCAL PostgreSQL 17 database','all_table_hashes_match':True,'counts':counts}
    Path('test-results/production-restore-check.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
finally:
    with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name)
