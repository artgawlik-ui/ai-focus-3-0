"""Local synthetic benchmark only. No export/restore, real providers or production SQL."""
import os,sys,json,time,uuid,subprocess,statistics,logging,types
from pathlib import Path
from datetime import datetime,timedelta,timezone
os.environ['APP_ENV']='test'
import psycopg
from sqlalchemy import create_engine,text,event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
source=make_url(os.environ['DATABASE_URL'])
if source.database!='focus3_test' or source.host not in ('localhost','127.0.0.1','postgres'):raise SystemExit('Refusing non-local/non-test benchmark')
from backend.db import Base,User,engine as default_engine
from backend.native_models import NativeBase
from backend.security import database,ph
from backend.main import app
from backend.native_queries import CONTACT_BASE,CONTACT_WHERE,CONTACT_ORDER,contact_params,TASK_FROM,TASK_WHERE,TASK_ORDER,task_params
from backend.native_notifications import generate
from backend import native_planning as native
from tests.native_scale_data import seed
from fastapi.testclient import TestClient
for name in ('focus','httpx','httpcore'):logging.getLogger(name).setLevel(logging.ERROR)
for key in ('FOCUS_CALENDAR_ENABLED','FOCUS_CALENDAR_SCHEMA_ENABLED'):os.environ[key]='true'
legacy=types.ModuleType('synthetic_legacy_native');sys.modules[legacy.__name__]=legacy
exec(compile(subprocess.check_output(['git','show','ffeabe0c1b9412d1117fa45ec3a04ea0be55630f:backend/native_planning.py'],text=True),'synthetic_legacy_native','exec'),legacy.__dict__)
output=Path('docs/sessions/session-022/performance');output.mkdir(parents=True,exist_ok=True)
reference_path=output/'pre-feed-role'/'measurements.json'
reference={r['salons']:r for r in json.loads(reference_path.read_text())['results']} if reference_path.exists() else {}
results=[];password='SyntheticOnlyBench123!';password_hash=ph.hash(password)
admin=source.set(database='postgres').render_as_string(hide_password=False)

def timings(c,path,runs=5):
    values=[];size=0
    for i in range(runs+1):
        start=time.perf_counter();response=c.get(path);elapsed=(time.perf_counter()-start)*1000
        assert response.status_code==200,'Synthetic benchmark endpoint failed'
        if i:values.append(elapsed)
        size=len(response.content)
    return {'median_ms':round(statistics.median(values),3),'min_ms':round(min(values),3),'max_ms':round(max(values),3),'samples_ms':[round(v,3) for v in values],'payload_bytes':size}

for count in (300,1000,5000,10000):
    print(json.dumps({'phase':'seed','salons':count}),flush=True)
    name='focus3_scale_'+uuid.uuid4().hex[:10];target=source.set(database=name).render_as_string(hide_password=False)
    with psycopg.connect(admin,autocommit=True) as db:db.execute('CREATE DATABASE '+name)
    engine=create_engine(target.replace('postgresql://','postgresql+psycopg://'),hide_parameters=True,pool_size=2,max_overflow=0)
    factory=sessionmaker(engine,expire_on_commit=False)
    env={**os.environ,'DATABASE_URL':target}
    try:
        Base.metadata.create_all(engine);NativeBase.metadata.create_all(engine)
        with factory() as db:
            db.add(User(id='manager',name='Synthetic manager',email='manager@synthetic.invalid',role='manager',password_hash=password_hash))
            for i in range(1,6):db.add(User(id='rep'+str(i),name='Synthetic rep'+str(i),email='rep'+str(i)+'@synthetic.invalid',role='sales',password_hash=password_hash))
            db.commit();seed(db,count,owners=tuple('rep'+str(i) for i in range(1,6)))
            version=db.scalar(text('SHOW server_version'))
        def dep():
            with factory() as db:yield db
        app.dependency_overrides[database]=dep
        client=TestClient(app);auth=client.post('/api/auth/login',json={'email':'manager@synthetic.invalid','password':password});assert auth.status_code==200
        user=types.SimpleNamespace(id='manager',role='manager')
        if count in reference:
            baseline=dict(reference[count]['legacy_monitor']);baseline['reference']='pre-feed-role/measurements.json (same function/data shape, prior run)'
        else:
            statements=[]
            def counter(*args):statements.append(1)
            event.listen(engine,'before_cursor_execute',counter)
            with factory() as db:
                start=time.perf_counter();old=legacy.list_due(db,user,native.today());legacy_ms=(time.perf_counter()-start)*1000
            event.remove(engine,'before_cursor_execute',counter)
            assert len(old)==count
            baseline={'elapsed_ms':round(legacy_ms,3),'sql_queries':len(statements)}
        print(json.dumps({'phase':'legacy_reference','salons':count,**baseline}),flush=True)
        row={'salons':count,'tasks':count,'visits':count,'activities':count*2,'server_version':version,'legacy_monitor':baseline}
        row['before_indexes']=timings(client,'/api/focus-calendar/contacts/page?limit=20',runs=3)
        for args in [('stamp','006'),('upgrade','007'),('check',)]:
            r=subprocess.run([sys.executable,'-m','alembic','-c','native-alembic.ini',*args],env=env,capture_output=True,timeout=30)
            assert r.returncode==0,'Synthetic index migration failed'
        with engine.connect() as db:db.execute(text('ANALYZE'));db.commit()
        notification_batches=[];start=time.perf_counter()
        for _ in range((count+499)//500+2):
            with factory() as db:n=generate(db);db.commit()
            notification_batches.append(n)
            if n==0:break
        row['reminders']={'inserted':sum(notification_batches),'batches':notification_batches,'elapsed_ms':round((time.perf_counter()-start)*1000,3)}
        assert row['reminders']['inserted']==count*2
        day=(datetime.now(timezone.utc)+timedelta(hours=1)).astimezone(native.ZONE).date().isoformat()
        notice_client=TestClient(app);notice_auth=notice_client.post('/api/auth/login',json={'email':'rep1@synthetic.invalid','password':password});assert notice_auth.status_code==200
        row['api']={}
        for key,path in [('contacts','/contacts/page?limit=20'),('tasks','/tasks/page?limit=20'),('visits','/visits/page?limit=20&day='+day),('notifications','/notifications/page?limit=20'),('report','/report')]:row['api'][key]=timings(notice_client if key=='notifications' else client,'/api/focus-calendar'+path)
        row['notification_reader']={'role':'sales','feed_total':notice_client.get('/api/focus-calendar/notifications/page').json()['total']}
        start=time.perf_counter();ids=[]
        for offset in range(0,count,100):
            data=client.get('/api/focus-calendar/contacts/page?limit=100&offset='+str(offset)).json()
            assert data['total']==count;ids.extend(r['salon_id'] for r in data['items'])
        assert len(ids)==len(set(ids))==count
        row['pagination']={'records_seen':len(ids),'unique':len(set(ids)),'page_size':100,'pages':(count+99)//100,'elapsed_ms':round((time.perf_counter()-start)*1000,3)}
        with factory() as db:
            cp=contact_params(user,native.today());tp=task_params(user)
            from backend.native_notifications import SOURCES
            moment=datetime.now(timezone.utc).isoformat()
            plans={
                'contacts':db.scalar(text('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+CONTACT_BASE+'SELECT * FROM projection'+CONTACT_WHERE+' ORDER BY '+CONTACT_ORDER+' LIMIT 20'),cp),
                'tasks':db.scalar(text('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT t.* '+TASK_FROM+TASK_WHERE+' ORDER BY '+TASK_ORDER+' LIMIT 20'),tp),
                'visits':db.scalar(text("EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) SELECT a.id FROM appointments a JOIN salons s ON s.id=a.salon_id WHERE a.starts_at>=:from AND a.starts_at<:to ORDER BY a.starts_at,a.id LIMIT 20"),{'from':datetime.now(timezone.utc).isoformat(),'to':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()}),
                'notifications':db.scalar(text('EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) '+SOURCES+'SELECT n.key,l.title,n.at FROM live l JOIN focus_notifications n ON n.key=l.key AND n.user_id=l.user_id WHERE n.user_id=:user ORDER BY n.at DESC,n.key LIMIT 20'),{'now':moment,'user':'rep1','reader':'rep1'}),
            }
        (output/('explain-'+str(count)+'.json')).write_text(json.dumps(plans,indent=2,default=str))
        results.append(row);(output/'measurements.json').write_text(json.dumps({'synthetic':True,'production':False,'postgres_cpu_limit':1,'postgres_memory_mib':512,'api_process':'host Python TestClient; not Render hardware','clock':'perf_counter','samples':'one warm-up then five samples (before indexes three)','results':results},indent=2))
        print(json.dumps({'phase':'complete','salons':count,'contacts_ms':row['api']['contacts']['median_ms'],'tasks_ms':row['api']['tasks']['median_ms'],'report_ms':row['api']['report']['median_ms'],'pagination':row['pagination'],'reminders':row['reminders']}),flush=True)
    finally:
        app.dependency_overrides.pop(database,None);engine.dispose()
        with psycopg.connect(admin,autocommit=True) as db:db.execute('DROP DATABASE '+name+' WITH (FORCE)')
