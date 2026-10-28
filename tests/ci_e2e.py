"""Synthetic browser suite for CI. Creates and drops only a fresh local test database."""
import os,json,uuid,subprocess,sys,time,tempfile
from pathlib import Path
import psycopg,httpx
from sqlalchemy.engine import make_url
source=make_url(os.environ['DATABASE_URL'])
if source.host not in ('localhost','127.0.0.1'):raise SystemExit('CI E2E requires a local PostgreSQL instance')
name='focus3_ci_'+uuid.uuid4().hex[:8]
admin=source.set(database='postgres').render_as_string(hide_password=False)
url=source.set(database=name).render_as_string(hide_password=False)
with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
child=None;proxy=None
credential_fd,credential_name=tempfile.mkstemp(prefix='focus3-ci-',suffix='.json')
os.close(credential_fd)
credential_path=Path(credential_name)
try:
    env={**os.environ,'AGENT_V2_ENABLED':'true','AI_PAID_PROCESSING_APPROVED':'false','DATABASE_URL':url,'APP_ENV':'test','PORT':'8005','APP_ORIGIN':'http://127.0.0.1:8006','FOCUS_TEST_ORIGIN':'http://127.0.0.1:8006','FOCUS_TEST_OFFLINE_FLAG':'/tmp/focus3-test-network-down','FOCUS_TEST_CREDENTIAL_FILE':str(credential_path)}
    os.environ.update({k:env[k] for k in ['DATABASE_URL','APP_ENV']})
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,check=True)
    from backend.db import Session,User,Salon
    from backend.security import ph
    from backend.main import key
    import secrets
    password=secrets.token_urlsafe(32)
    with Session() as db:
        db.add(User(id='ci-manager',email='verification@focus.invalid',name='Weryfikacja techniczna',role='manager',password_hash=ph.hash(password)));db.flush()
        db.add(Salon(id=str(uuid.uuid4()),owner_id='ci-manager',name='[TEST TECHNICZNY] Ai Focus 3.0',city='Głogów',notes='Synthetic CI data',dedup_key=key('[TEST TECHNICZNY] Ai Focus 3.0','Głogów')));db.commit()
    credential_path.write_text(json.dumps({'email':'verification@focus.invalid','password':password}));credential_path.chmod(0o600)
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
finally:
    Path('/tmp/focus3-test-network-down').unlink(missing_ok=True);credential_path.unlink(missing_ok=True)
    if proxy:proxy.terminate();proxy.wait(timeout=10)
    if child:child.terminate();child.wait(timeout=30)
    try:
        from backend.db import engine
        engine.dispose()
    except ImportError:pass
    with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name)
