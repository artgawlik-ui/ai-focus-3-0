"""Optional local synthetic process budget probe; never connects to production."""
import os,sys,time,json,uuid,subprocess,threading,hmac,hashlib,secrets
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import psycopg,httpx
from sqlalchemy.engine import make_url
from cryptography.fernet import Fernet

def main():
    source=make_url(os.environ['DATABASE_URL'])
    if source.host not in ('localhost','127.0.0.1') or source.database!='focus3_test':raise SystemExit('Local test database required')
    name='focus3_budget_'+uuid.uuid4().hex[:10]
    admin=source.set(database='postgres').render_as_string(hide_password=False)
    target=source.set(database=name).render_as_string(hide_password=False)
    env={**os.environ,'DATABASE_URL':target,'APP_ENV':'test','PORT':'8017','META_ENABLED':'false','META_OAUTH_ENABLED':'false','META_INGEST_ENABLED':'true','META_CRM_HISTORY_ENABLED':'true','META_MODE':'development','META_APP_SECRET':secrets.token_urlsafe(32),'META_ENCRYPTION_KEY':Fernet.generate_key().decode(),'META_TEST_ACCOUNT_ID':'90001','AI_PAID_PROCESSING_APPROVED':'false','OFFSITE_BACKUP_ENABLED':'false'}
    with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
    process=None;stop=threading.Event();peak={'rss_kib':0,'threads':0};ticks=[]
    def sample():
        while not stop.is_set():
            try:
                snapshot=subprocess.check_output(['ps','-eo','pid=,ppid=,rss=,nlwp=,cputimes='],text=True)
                rows=[list(map(int,line.split())) for line in snapshot.splitlines()]
                selected=[r for r in rows if r[0]==process.pid or r[1]==process.pid]
                rss=sum(r[2] for r in selected);threads=sum(r[3] for r in selected);cpu=sum(r[4] for r in selected)
                peak['rss_kib']=max(peak['rss_kib'],rss);peak['threads']=max(peak['threads'],threads);ticks.append(cpu)
            except (OSError,StopIteration):pass
            stop.wait(.1)
    try:
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        # Seed via an isolated child so its engine cannot point at a caller's DB.
        seed="from backend.db import Session,User; from backend.security import ph; import os; db=Session(); db.add(User(id='fixture',email='fixture@invalid.test',name='Fixture',role='manager',password_hash=ph.hash(os.environ['PROBE_PASSWORD']))); db.commit()"
        password=secrets.token_urlsafe(32);subprocess.run([sys.executable,'-c',seed],env={**env,'PROBE_PASSWORD':password},check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        process=subprocess.Popen([sys.executable,'-m','scripts.supervise'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        sampler=threading.Thread(target=sample);sampler.start();start=time.monotonic()
        with httpx.Client(timeout=10,trust_env=False) as c:
            for _ in range(100):
                try:
                    if c.get('http://127.0.0.1:8017/api/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            def login(_):
                return httpx.post('http://127.0.0.1:8017/api/auth/login',json={'email':'fixture@invalid.test','password':password},timeout=10,trust_env=False).status_code
            with ThreadPoolExecutor(max_workers=2) as pool:assert list(pool.map(login,range(2)))==[200,200]
            durations=[]
            for i in range(20):
                payload={'object':'instagram','entry':[{'id':'90001','messaging':[{'sender':{'id':'90002'},'recipient':{'id':'90001'},'timestamp':int(time.time()*1000),'message':{'mid':'budget-'+str(i),'text':'Syntetyczna odpowiedź'}}]}]}
                raw=json.dumps(payload).encode();signature='sha256='+hmac.new(env['META_APP_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
                before=time.monotonic();response=c.post('http://127.0.0.1:8017/api/meta/webhook',content=raw,headers={'X-Hub-Signature-256':signature});durations.append(time.monotonic()-before);assert response.status_code==200
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                with psycopg.connect(target) as db:done=db.execute("SELECT COUNT(*) FROM meta_webhook_inbox WHERE status='done'").fetchone()[0]
                if done==20:break
                time.sleep(.25)
            assert done==20
        elapsed=time.monotonic()-start;stop.set();sampler.join()
        result={**peak,'rss_mib':round(peak['rss_kib']/1024,2),'wall_seconds':round(elapsed,2),'process_cpu_seconds':round(max(ticks)-min(ticks),2),'webhooks':20,'processed':done,'max_ack_ms':round(max(durations)*1000,2),'scope':'local supervisor + API + existing agent; not Render quota, no backup process, no real Meta API'}
        Path('test-results/meta-303-resources.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:
        stop.set()
        if process:process.terminate();process.wait(timeout=30)
        with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name+' WITH (FORCE)')

if __name__=='__main__':main()
