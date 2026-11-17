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
fixture_dir=tempfile.TemporaryDirectory(prefix='focus3-e2e-http-')
Path(fixture_dir.name,'sitecustomize.py').write_text('import os\ntry:\n from tests.e2e_network_guard import install as network_guard\n network_guard()\n from tests.e2e_discovery_transport import install\n install()\nexcept BaseException:\n os._exit(78)\n')
credential_fd,credential_name=tempfile.mkstemp(prefix='focus3-ci-',suffix='.json')
os.close(credential_fd)
credential_path=Path(credential_name)
try:
    env={**os.environ,'AGENT_V2_ENABLED':'true','AI_PAID_PROCESSING_APPROVED':'false','DATABASE_URL':url,'APP_ENV':'test','PORT':'8005','APP_ORIGIN':'http://127.0.0.1:8006','FOCUS_TEST_ORIGIN':'http://127.0.0.1:8006','FOCUS_TEST_OFFLINE_FLAG':'/tmp/focus3-test-network-down','FOCUS_TEST_CREDENTIAL_FILE':str(credential_path)}
    env.update({'FOCUS_TEST_EXTERNAL_ATTEMPTS':str(Path(fixture_dir.name)/'external-attempts.jsonl'),'SALES_WORKFLOW_ENABLED':'true','DISCOVERY_RADIUS_ENABLED':'true','VISIT_PLANNER_ENABLED':'true','PYTHONPATH':fixture_dir.name+os.pathsep+str(Path(__file__).resolve().parents[1])})
    env.update({'FOCUS_DIAGNOSTICS_ENABLED':'true','FOCUS_CALENDAR_SCHEMA_ENABLED':'true','FOCUS_CALENDAR_ENABLED':'true','GOOGLE_SCHEMA_ENABLED':'false','GOOGLE_CALENDAR_ENABLED':'false','GOOGLE_CALENDAR_WRITE_ENABLED':'false','GOOGLE_CLIENT_ID':'synthetic-google-client','GOOGLE_CLIENT_SECRET':'synthetic-google-secret','GOOGLE_REDIRECT_URI':'http://127.0.0.1:8006/api/google-calendar/oauth/callback','GOOGLE_ENCRYPTION_KEY':__import__('cryptography.fernet',fromlist=['Fernet']).Fernet.generate_key().decode(),'FOCUS_TEST_GOOGLE_STORE':str(Path(fixture_dir.name)/'google.json'),'FOCUS_TEST_INVALID_QUEUE_TIME_FLAG':str(Path(fixture_dir.name)/'invalid-queue-time')})
    from cryptography.fernet import Fernet
    env.update({'META_ENABLED':'true','META_MODE':'development','META_APP_ID':'123456','META_CONFIG_ID':'ci-synthetic','META_APP_SECRET':uuid.uuid4().hex,'META_VERIFY_TOKEN':uuid.uuid4().hex,'META_ENCRYPTION_KEY':Fernet.generate_key().decode(),'META_TEST_ACCOUNT_ID':'90001','META_REDIRECT_URI':'https://test.invalid/api/meta/oauth/callback','BOOTSTRAP_EMAIL':'verification@focus.invalid'})
    os.environ.update({k:env[k] for k in ['DATABASE_URL','APP_ENV']+list(k for k in env if k.startswith('META_'))})
    subprocess.run([sys.executable,'-m','alembic','-c','native-alembic.ini','upgrade','head'],env=env,check=True)
    from backend.db import Session,User,Salon
    from backend.security import ph
    from backend.main import key
    import secrets
    password=secrets.token_urlsafe(32)
    with Session() as db:
        db.add(User(id='ci-manager',email='verification@focus.invalid',name='Weryfikacja techniczna',role='manager',password_hash=ph.hash(password)));db.flush()
        db.add(Salon(id=str(uuid.uuid4()),owner_id='ci-manager',name='[TEST TECHNICZNY] Ai Focus 3.0',city='Głogów',notes='Synthetic CI data',dedup_key=key('[TEST TECHNICZNY] Ai Focus 3.0','Głogów')));db.commit()
    from backend.meta_models import MetaConversation,MetaMessage,MetaCredential
    from backend.meta import seal
    from backend.db import now
    with Session() as db:
        salon=db.query(Salon).first()
        conversation=MetaConversation(id=str(uuid.uuid4()),account_id='90001',peer_id='90002',salon_id=salon.id,last_inbound_at=now());db.add(conversation);db.flush()
        db.add(MetaMessage(id=str(uuid.uuid4()),conversation_id=conversation.id,external_id='ci-message',status='received',direction='inbound',body_ciphertext=seal('message','Syntetyczna odpowiedź: proszę o termin wizyty.'),occurred_at=now()))
        db.add(MetaCredential(account_id='90001',business_id='ci-business',subject_id='ci-subject',username='synthetic_test',config_id='ci-synthetic',token_ciphertext=seal('token','synthetic-never-call-api'),expires_at='',checked_at=now()))
        db.commit()
    credential_path.write_text(json.dumps({'email':'verification@focus.invalid','password':password}));credential_path.chmod(0o600)
    child=subprocess.Popen([sys.executable,'-m','scripts.supervise'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            if httpx.get('http://127.0.0.1:8005/api/health').status_code==200:break
        except Exception:pass
        time.sleep(.2)
    Path('/tmp/focus3-test-network-down').unlink(missing_ok=True)
    proxy=subprocess.Popen([sys.executable,'-m','tests.offline_proxy'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(.5)
    subprocess.run([sys.executable,'-m','tests.production_browser_check'],env=env,check=True)
    subprocess.run([sys.executable,'-m','tests.sales_day_browser'],env=env,check=True)
    if Path(env['FOCUS_TEST_EXTERNAL_ATTEMPTS']).exists():raise AssertionError('An external transport was attempted during E2E')
finally:
    Path('/tmp/focus3-test-network-down').unlink(missing_ok=True);credential_path.unlink(missing_ok=True)
    if proxy:proxy.terminate();proxy.wait(timeout=10)
    if child:child.terminate();child.wait(timeout=30)
    try:
        from backend.db import engine
        engine.dispose()
    except ImportError:pass
    with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name)
    fixture_dir.cleanup()
