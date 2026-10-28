"""Restore actual encrypted snapshot locally; run all write E2E checks on that isolated copy."""
import os,json,uuid,subprocess,sys,time
from pathlib import Path
import psycopg,httpx
from scripts.backup import restore
secrets=json.loads(Path('.render-auth/verification.json').read_text())
name='focus3_release_'+uuid.uuid4().hex[:8]
admin='postgresql://postgres@127.0.0.1:55432/postgres'
url='postgresql://postgres@127.0.0.1:55432/'+name
with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
child=None;proxy=None
try:
    os.environ['RESTORE_DATABASE_URL']=url;os.environ['BACKUP_PASSPHRASE']=secrets['backup_passphrase']
    os.environ['PATH']=str(Path('.tools').resolve())+os.pathsep+os.environ['PATH']
    restore('.render-auth/production-backup.enc')
    env={**os.environ,'DATABASE_URL':url,'APP_ENV':'test','PORT':'8005','FOCUS_TEST_ORIGIN':'http://127.0.0.1:8006','APP_ORIGIN':'http://127.0.0.1:8006','FOCUS_TEST_OFFLINE_FLAG':'/tmp/focus3-test-network-down'}
    child=subprocess.Popen([sys.executable,'-m','scripts.supervise'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            if httpx.get('http://127.0.0.1:8005/api/health').status_code==200:break
        except Exception:pass
        time.sleep(.2)
    Path('/tmp/focus3-test-network-down').unlink(missing_ok=True)
    proxy=subprocess.Popen([sys.executable,'-m','tests.offline_proxy'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(.5)
    subprocess.run([sys.executable,'tests/production_browser_check.py'],env=env,check=True)
    print('PASS: Chromium desktop and WebKit iPhone E2E on isolated restored production copy')
finally:
    Path('/tmp/focus3-test-network-down').unlink(missing_ok=True)
    if proxy:proxy.terminate();proxy.wait(timeout=10)
    if child:child.terminate();child.wait(timeout=30)
    with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name)
