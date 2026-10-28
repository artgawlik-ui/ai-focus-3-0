"""Encrypted pg_dump backup; database credentials are passed via child environment."""
import os, subprocess, json, hashlib, tempfile
from pathlib import Path
from datetime import datetime, timezone
import psycopg
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from backend.db import Base

def pg_env(url):
    info=psycopg.conninfo.conninfo_to_dict(url.replace('postgresql+psycopg://','postgresql://'))
    result=os.environ.copy()
    for k,v in info.items():
        env={'host':'PGHOST','port':'PGPORT','dbname':'PGDATABASE','user':'PGUSER','password':'PGPASSWORD','sslmode':'PGSSLMODE'}.get(k)
        if env: result[env]=str(v)
    return result

def fingerprint(url):
    result={}
    with psycopg.connect(url.replace('postgresql+psycopg://','postgresql://')) as db:
        for table in sorted(Base.metadata.tables):
            rows=db.execute('SELECT row_to_json(t)::text FROM "'+table+'" t').fetchall()
            canonical=sorted(json.dumps(json.loads(row[0]),sort_keys=True,ensure_ascii=False,separators=(',',':')) for row in rows)
            result[table]={'count':len(rows),'sha256':hashlib.sha256('\n'.join(canonical).encode()).hexdigest()}
    return result

def derive(passphrase,salt):
    return Scrypt(salt=salt,length=32,n=2**15,r=8,p=1).derive(passphrase.encode())

def backup(path, url=None, phrase=None):
    url=url or os.environ['DATABASE_URL']; phrase=phrase or os.environ['BACKUP_PASSPHRASE']
    if len(phrase)<20: raise ValueError('Backup passphrase requires 20+ characters')
    # Short maintenance lock ensures the dump and verification manifest see identical data.
    with psycopg.connect(url.replace('postgresql+psycopg://','postgresql://')) as lock:
        lock.execute("SET LOCAL lock_timeout='5s'")
        tables=lock.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        from psycopg import sql
        for (table,) in tables:
            lock.execute(sql.SQL('LOCK TABLE {} IN SHARE MODE').format(sql.Identifier(table)))
        raw=subprocess.run(['pg_dump','--format=custom','--no-owner','--no-acl'],env=pg_env(url),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=120).stdout
        payload=json.dumps({'format':1,'created_at':datetime.now(timezone.utc).isoformat(),'fingerprint':fingerprint(url)}).encode()+b'\n'+raw
    salt=os.urandom(16); nonce=os.urandom(12)
    encrypted=b'FOCUS3B1'+salt+nonce+AESGCM(derive(phrase,salt)).encrypt(nonce,payload,b'focus3-backup')
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(descriptor,'wb') as f: f.write(encrypted)
    print('Encrypted backup created. Restore verification required.')

def restore(path):
    # Target must be a separately provisioned EMPTY database; no drop/clean options.
    url=os.environ['RESTORE_DATABASE_URL']
    if url==os.getenv('DATABASE_URL'): raise ValueError('Refusing restore to source database')
    with psycopg.connect(url) as db:
        if db.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'").fetchone()[0]:
            raise ValueError('Restore target must be empty')
    data=Path(path).read_bytes()
    if data[:8]!=b'FOCUS3B1': raise ValueError('Unknown backup format')
    salt,nonce=data[8:24],data[24:36]
    payload=AESGCM(derive(os.environ['BACKUP_PASSPHRASE'],salt)).decrypt(nonce,data[36:],b'focus3-backup')
    manifest,raw=payload.split(b'\n',1)
    subprocess.run(['pg_restore','--dbname='+psycopg.conninfo.conninfo_to_dict(url).get('dbname',''),'--no-owner','--no-acl','--single-transaction','--exit-on-error'],input=raw,env=pg_env(url),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    actual=fingerprint(url)
    if actual!=json.loads(manifest)['fingerprint']: raise ValueError('Restored fingerprint mismatch. Keep source unchanged; investigate concurrent writes.')
    print('Restore verified: every table count and content fingerprint matches.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['backup','restore']);p.add_argument('path');args=p.parse_args()
    try: (backup if args.action=='backup' else restore)(args.path)
    except Exception as e: raise SystemExit('Backup operation failed: '+type(e).__name__)
