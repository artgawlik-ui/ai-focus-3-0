"""Full API + worker check, followed by service restart durability."""
import os, json, subprocess, sys, time, uuid
import httpx
base='http://127.0.0.1:8004'
env={**os.environ,'APP_ENV':'test','PORT':'8004','DATABASE_URL':'postgresql://postgres@127.0.0.1:55432/focus3_e2e'}
def start():
    child=subprocess.Popen([sys.executable,'-m','scripts.supervise'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(80):
        try:
            if httpx.get(base+'/api/health').status_code==200:return child
        except Exception:pass
        time.sleep(.2)
    child.terminate();raise RuntimeError('Service not ready')
def login():
    client=httpx.Client(base_url=base,timeout=15)
    result=client.post('/api/auth/login',json={'email':'e2e@focus.test','password':'E2eSyntheticPassword123!'})
    result.raise_for_status();client.headers['X-CSRF-Token']=result.json()['csrf'];return client
child=start()
try:
    client=login()
    s=client.post('/api/salons',json={'name':'Restart test '+uuid.uuid4().hex[:8],'city':'Głogów'});s.raise_for_status();salon=s.json()
    job=client.post('/api/agent/jobs',json={'salon_id':salon['id']});job.raise_for_status();job_id=job.json()['id']
    for _ in range(80):
        result=next(j for j in client.get('/api/agent/jobs').json() if j['id']==job_id)
        if result['status']=='completed':break
        time.sleep(.2)
    assert result['status']=='completed',result['status']
    assert json.loads(result['result'])['sent'] is False
    client.close();child.terminate();child.wait(timeout=30)
    child=start();client=login()
    assert client.get('/api/salons/'+salon['id']).json()['name']==salon['name']
    assert next(j for j in client.get('/api/agent/jobs').json() if j['id']==job_id)['status']=='completed'
    assert any(a['kind']=='agent_draft' for a in client.get('/api/salons/'+salon['id']+'/activities').json())
    print('PASS: separate worker processed queued job; CRM, audit and job survived service restart')
finally:
    child.terminate();child.wait(timeout=30)
