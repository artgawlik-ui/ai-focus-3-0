"""Offline sales-day acceptance: real local PG/API/UI, OSM fixture, signed inbound fixture.
No external navigation or API allowed. Manual actions are synthetic operator declarations.
"""
import os,json,uuid,time,hashlib,hmac
from datetime import datetime,timedelta,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from scripts.local_test_policy import local_origin
origin=local_origin()
assert origin.startswith('http://127.0.0.1:') and os.getenv('APP_ENV')=='test'
credentials=json.loads(Path(os.environ['FOCUS_TEST_CREDENTIAL_FILE']).read_text())
results=[]
Path('test-results').mkdir(exist_ok=True)
from tests.e2e_network_guard import self_probe
probe=self_probe(Path(os.environ['FOCUS_TEST_EXTERNAL_ATTEMPTS']).parent)
print('Network negative control: PASS (blocked before socket, sanitized recorder)',flush=True)

def login(page,email,password):
    page.goto(origin);page.get_by_label('E-mail').fill(email);page.get_by_label('Hasło',exact=True).fill(password)
    page.get_by_role('button',name='Wejdź do swojej przestrzeni').click();page.get_by_text('Salony w bazie',exact=True).wait_for()
    return page.request.get(origin+'/api/auth/me').json()['csrf']
def request(context,csrf,path,method='GET',payload=None,code=200):
    r=context.request.fetch(origin+'/api'+path,method=method,data=payload,headers={'X-CSRF-Token':csrf})
    assert r.status==code,(path,r.status,r.text()[:200]);return r.json()
def synthetic_db():
    import psycopg
    from sqlalchemy.engine import make_url
    target=make_url(os.environ['DATABASE_URL'])
    assert target.host in ('localhost','127.0.0.1') and target.database.startswith('focus3_ci_')
    return psycopg.connect(os.environ['DATABASE_URL'])

def nav(page,label,mobile):
    if mobile:page.get_by_label('Otwórz menu').click()
    page.get_by_role('button',name=label,exact=True).click()
def salon_dialog(page,name,mobile):
    nav(page,'Baza salonów',mobile);page.get_by_label('Szukaj salonu').fill(name)
    page.get_by_text(name,exact=True).click();page.get_by_role('dialog').wait_for()
    return page.get_by_label('Ręczny kontakt Instagram',exact=True)

with sync_playwright() as p:
    for label,engine,options,executable in [('chromium',p.chromium,{'viewport':{'width':1365,'height':950}},os.getenv('FOCUS_TEST_CHROMIUM_EXECUTABLE','/usr/bin/chromium')),('webkit',p.webkit,p.devices['iPhone 13'],os.getenv('FOCUS_TEST_WEBKIT_EXECUTABLE','/workspace/ai-focus-3-0/.tools/run-webkit.sh'))]:
        browser=engine.launch(headless=True,executable_path=executable if Path(executable).exists() else None,args=['--no-sandbox'] if label=='chromium' else [])
        # Fault-injection routing must bypass SW ownership of fetch in WebKit.
        # The unchanged production_browser_check separately tests the real SW/PWA/offline path.
        m=browser.new_context(**options,service_workers='block');rep=browser.new_context(**options,service_workers='block');mobile=label=='webkit'
        # Never open even a public Instagram URL during acceptance.
        browser_external=[]
        def route_local(route):
            if route.request.url.startswith(origin+'/'):return route.continue_()
            browser_external.append('external_http');return route.abort()
        for context in (m,rep):context.route('**/*',route_local)
        print(label+': sales-day start',flush=True)
        page=m.new_page();csrf=login(page,credentials['email'],credentials['password'])
        email='sales-'+label+'@focus.invalid';password=uuid.uuid4().hex+'!'
        u=request(m,csrf,'/users','POST',{'email':email,'name':'Handlowiec '+label,'password':password,'role':'sales'},201)
        rp=rep.new_page();rcsrf=login(rp,email,password)
        discovery=request(rep,rcsrf,'/discovery?city=G%C5%82og%C3%B3w')['items'][0]
        salons=[]
        for n in range(10):
            payload={'name':'[SYNTHETIC DAY] '+label+' '+str(n),'city':'Głogów','instagram':'@synthetic_day_'+str(n),'specialization':'koloryzacja','source_url':discovery['source_url'],'potential':4000,'priority':'A+' if n==0 else 'A','stage':'new'}
            s=request(rep,rcsrf,'/salons','POST',payload,201);salons.append(s)
            if n==0:request(rep,rcsrf,'/salons','POST',payload,409)
        s=salons[0];base='/salons/'+s['id']
        # Worker scoring remains CRM-based; no paid model.
        request(rep,rcsrf,'/agent/jobs','POST',{'salon_id':s['id']},202)
        for _ in range(80):
            jobs=request(rep,rcsrf,'/agent/jobs');job=next(x for x in jobs if x['salon_id']==s['id'])
            if job['status']=='completed':break
            time.sleep(.1)
        assert job['status']=='completed';analysis=json.loads(job['result']);assert analysis['priority_suggestion']=='A' and analysis['sent'] is False
        print(label+': fixtures and scoring PASS',flush=True)
        # Mobile rep verifies profile and prepares draft through actual UI.
        panel=salon_dialog(rp,s['name'],mobile)
        expect(panel.get_by_role('link',name='Otwórz profil Instagram')).to_have_attribute('href','https://www.instagram.com/synthetic_day_0/')
        panel.get_by_label('Dowód ręcznej weryfikacji tożsamości i specjalizacji').fill('Dane syntetyczne zgodne ze źródłem OSM')
        panel.get_by_role('button',name='Potwierdzam zgodność profilu z salonem').click()
        panel.get_by_role('button',name='Przygotuj indywidualny szkic DM').click()
        expect(panel.locator('blockquote')).to_contain_text('koloryzacja')
        assert panel.get_by_role('button',name='Wysłano ręcznie',exact=True).count()==0
        state=request(rep,rcsrf,base+'/instagram-contact');draft=next(e for e in state['events'] if e['kind']=='sales_draft')
        assert not state['api_confirmed_sent']
        # Renew an eight-day UNSENT draft through the actual UI; keep the old ledger.
        expired_id=draft['id']
        request(rep,rcsrf,base+'/instagram-events','POST',{'draft_id':expired_id,'request_id':str(uuid.uuid4()),'action':'not_sent','confirmed':True,'note':'Syntetyczny szkic nie został wysłany'})
        with synthetic_db() as sql:
            assert sql.execute('UPDATE activities SET created_at=%s WHERE id=%s AND kind=%s',((datetime.now(timezone.utc)-timedelta(days=8)).isoformat(),expired_id,'sales_draft')).rowcount==1
        request(m,csrf,base+'/instagram-events','POST',{'draft_id':expired_id,'request_id':str(uuid.uuid4()),'action':'manual_sent','confirmed':True,'note':'Próba użycia przeterminowanego szkicu — fixture'},409)
        with rp.expect_response(lambda response:response.url==origin+'/api'+base+'/prepare-instagram') as renewal:
            panel.get_by_role('button',name='Przygotuj indywidualny szkic DM').click()
        assert renewal.value.status==201
        draft=renewal.value.json();assert draft['id']!=expired_id
        expect(panel).to_have_attribute('aria-busy','false')
        state=request(rep,rcsrf,base+'/instagram-contact')
        assert any(e['id']==expired_id for e in state['events'])
        assert sum(e['kind']=='sales_draft' for e in state['events'])==2
        assert not any(e['kind']=='instagram_manual' for e in state['events'])
        print(label+': eight-day unsent draft renewal PASS',flush=True)
        # Wrong profile rejected; no implicit update of verification.
        request(rep,rcsrf,base+'/verify-instagram','POST',{'profile':'wrong_profile','identity_confirmed':True,'evidence':'Synthetic wrong profile'},409)
        # Owner records only an explicit declaration, not API confirmation.
        mp=salon_dialog(page,s['name'],mobile)
        mp.get_by_label('Wynik kontaktu lub powód niewysłania').fill('Syntetyczne oświadczenie właściciela')
        mp.get_by_label('Potwierdzam rzeczywiste zdarzenie;',exact=False).check()
        def failed_save(route):route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'Syntetyczna awaria zapisu'}))
        page.route('**/instagram-events',failed_save)
        mp.get_by_role('button',name='Nie wysłano',exact=True).click()
        expect(mp.get_by_role('alert')).to_contain_text('Syntetyczna awaria zapisu')
        expect(mp.locator('textarea')).to_be_enabled()
        expect(mp.get_by_role('button',name='Wysłano ręcznie',exact=True)).to_be_enabled()
        assert not any(e['kind']=='instagram_manual' for e in request(m,csrf,base+'/instagram-contact')['events'])
        page.unroute('**/instagram-events',failed_save)
        held=[]
        def hold_save(route):
            held.append(route);page.locator('body').evaluate("element=>element.dataset.salesSaveHeld='true'")
        page.route('**/instagram-events',hold_save)
        # Two synchronous clicks beat React's next render: the ref guard must still admit one request.
        mp.get_by_role('button',name='Wysłano ręcznie',exact=True).evaluate('(button)=>{button.click();button.click()}')
        expect(page.locator('body')).to_have_attribute('data-sales-save-held','true')
        expect(mp.locator('textarea')).to_be_disabled()
        expect(mp.get_by_label('Potwierdzam rzeczywiste zdarzenie;',exact=False)).to_be_disabled()
        expect(mp.get_by_role('button',name='Nie wysłano',exact=True)).to_be_disabled()
        page.keyboard.press('Tab')
        assert not mp.locator('textarea').evaluate('(element)=>element===document.activeElement')
        assert len(held)==1
        saved_route=held[0];saved_response=saved_route.fetch();saved_route.fulfill(response=saved_response)
        page.unroute('**/instagram-events',hold_save)
        expect(mp.get_by_text('Wysłano ręcznie · deklaracja właściciela',exact=False)).to_be_visible()
        expect(mp.locator('textarea')).to_be_enabled()
        # Replay races do not create another send; dedicated PG test also sends concurrently.
        request(m,csrf,base+'/instagram-events','POST',{'draft_id':draft['id'],'request_id':str(uuid.uuid4()),'confirmed':True,'action':'manual_sent','note':'Duplicate synthetic declaration'},409)
        mp.get_by_label('Wynik kontaktu lub powód niewysłania').fill('Klient prosi o wizytę i inicjuje termin — fixture')
        mp.get_by_label('Potwierdzam rzeczywiste zdarzenie;',exact=False).check()
        mp.get_by_label('Klient sam zainicjował uzgodnienie terminu').check()
        mp.get_by_role('button',name='Odpowiedział',exact=True).click()
        expect(mp.get_by_text('Odpowiedział · zapis ręczny',exact=False)).to_be_visible()
        page.screenshot(path='test-results/sales-day-contact-'+label+'.png')
        tasks=request(rep,rcsrf,'/focus-calendar/tasks');assert sum(t['salon_id']==s['id'] and (t.get('cycle_key') or '').startswith('sales-reply:') for t in tasks)==1
        print(label+': manual workflow PASS',flush=True)
        # Proposal/confirmation/rescheduling/conflict use real API and planner UI.
        when='2027-05-18T10:00:00+02:00' if label=='chromium' else '2027-05-18T14:00:00+02:00'
        visit=request(rep,rcsrf,'/appointments','POST',{'salon_id':s['id'],'starts_at':when,'minutes':20},201)
        request(rep,rcsrf,'/appointments','POST',{'salon_id':s['id'],'starts_at':when,'minutes':20},409)
        visits=request(m,csrf,'/appointments?day=2027-05-18');v=next(v for v in visits if v['id']==visit['id'])
        moved=request(m,csrf,'/appointments/'+visit['id'],'PATCH',{'status':'confirmed','starts_at':when.replace(':00:00',':30:00'),'minutes':20,'confirmation_recorded':True,'expected_revision':v['revision']})
        page.get_by_label('Zamknij',exact=True).click();nav(page,'Kalendarz i trasy',mobile)
        page.get_by_label('Data planu',exact=True).fill('2027-05-18');page.get_by_label('Data planu',exact=True).press('Tab')
        expect(page.locator('.visit-card').filter(has=page.get_by_role('heading',name=s['name'],exact=True))).to_contain_text('Potwierdzona')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        # One refusal blocks CRM, worker and another draft.
        negative=salons[1];nb='/salons/'+negative['id']
        request(rep,rcsrf,nb+'/verify-instagram','POST',{'profile':negative['instagram'],'identity_confirmed':True,'evidence':'Syntetyczna zgodność profilu'})
        nd=request(rep,rcsrf,nb+'/prepare-instagram','POST',code=201)
        for action in ('manual_sent','refused'):
            request(m,csrf,nb+'/instagram-events','POST',{'draft_id':nd['id'],'request_id':str(uuid.uuid4()),'confirmed':True,'action':action,'note':'Syntetyczna rezygnacja z kontaktu'})
        request(rep,rcsrf,nb+'/prepare-instagram','POST',code=409)
        request(rep,rcsrf,'/agent/jobs','POST',{'salon_id':negative['id']},409)
        # A prior actual recorded call prevents another cold contact.
        prior=salons[2];pb='/salons/'+prior['id']
        request(rep,rcsrf,pb+'/activities','POST',{'kind':'call','body':'Syntetyczny wcześniejszy kontakt'},201)
        request(rep,rcsrf,pb+'/verify-instagram','POST',{'profile':prior['instagram'],'identity_confirmed':True,'evidence':'Syntetyczne potwierdzenie danych'})
        request(rep,rcsrf,pb+'/prepare-instagram','POST',code=409)
        print(label+': visits and opt-out PASS',flush=True)
        # Signed inbound is only a fixture; persist/process/dedupe/bind/opt-out via existing worker.
        peer='day-'+label;mid='mid-'+label
        def inbound(text,mid):
            payload={'object':'instagram','entry':[{'id':os.environ['META_TEST_ACCOUNT_ID'],'messaging':[{'sender':{'id':peer},'recipient':{'id':os.environ['META_TEST_ACCOUNT_ID']},'timestamp':int(time.time()*1000),'message':{'mid':mid,'text':text}}]}]}
            raw=json.dumps(payload).encode();sig='sha256='+hmac.new(os.environ['META_APP_SECRET'].encode(),raw,hashlib.sha256).hexdigest()
            r=m.request.post(origin+'/api/meta/webhook',data=raw,headers={'X-Hub-Signature-256':sig,'Content-Type':'application/json'});assert r.status==200
        inbound('Proszę o kontakt w sprawie wizyty — fixture',mid);inbound('Proszę o kontakt w sprawie wizyty — fixture',mid)
        for _ in range(80):
            conv=request(m,csrf,'/meta/conversations');unbound=[c for c in conv if not c['salon_id']]
            if unbound:break
            time.sleep(.1)
        assert len(unbound)==1;cid=unbound[0]['id']
        request(m,csrf,'/meta/conversations/'+cid+'/bind','POST',{'salon_id':salons[3]['id']})
        msgs=request(m,csrf,'/meta/conversations/'+cid+'/messages');assert len(msgs)==1 and msgs[0]['status']=='received'
        inbound('Nie kontaktuj się — fixture',mid+'-stop')
        for _ in range(80):
            if next(c for c in request(m,csrf,'/meta/conversations') if c['id']==cid)['opted_out']:break
            time.sleep(.1)
        assert next(c for c in request(m,csrf,'/meta/conversations') if c['id']==cid)['opted_out']
        assert request(rep,rcsrf,'/salons/'+salons[3]['id']+'/instagram-contact')['blocked']
        request(rep,rcsrf,'/agent/jobs','POST',{'salon_id':salons[3]['id']},409)
        request(rep,rcsrf,'/meta/conversations/'+cid+'/drafts','POST',{'text':'Forbidden fixture'},409)
        print(label+': signed inbound and deduplication PASS',flush=True)
        # Unauthorized peer is unable to read another rep's contact history.
        if label=='webkit':
            users=request(m,csrf,'/users');other=next(u for u in users if u['email']=='sales-chromium@focus.invalid')
            request(m,csrf,'/salons/'+salons[9]['id']+'/assign','POST',{'owner_id':other['id']})
            request(rep,rcsrf,'/salons/'+salons[9]['id']+'/instagram-contact',code=404)
        # A late response from a closed profile must not replace the newly opened salon.
        stale_base='/salons/'+salons[4]['id'];stale=[]
        def hold_stale(route):stale.append(route);rp.locator('body').evaluate("element=>element.dataset.staleContactHeld='true'")
        rep.route('**'+stale_base+'/instagram-contact',hold_stale)
        rp.get_by_label('Zamknij',exact=True).click()
        rp.get_by_label('Szukaj salonu').fill(salons[4]['name']);rp.get_by_text(salons[4]['name'],exact=True).click()
        expect(rp.locator('body')).to_have_attribute('data-stale-contact-held','true')
        rp.get_by_label('Zamknij',exact=True).click()
        rp.get_by_label('Szukaj salonu').fill(s['name']);rp.get_by_text(s['name'],exact=True).click()
        expect(rp.get_by_label('Ręczny kontakt Instagram').get_by_role('link',name='Otwórz profil Instagram')).to_have_attribute('href','https://www.instagram.com/synthetic_day_0/')
        assert len(stale)==1
        stale[0].fulfill(response=stale[0].fetch());rep.unroute('**'+stale_base+'/instagram-contact',hold_stale)
        expect(rp.get_by_role('dialog')).to_have_attribute('aria-label',s['name'])
        expect(rp.get_by_label('Ręczny kontakt Instagram').get_by_role('link',name='Otwórz profil Instagram')).to_have_attribute('href','https://www.instagram.com/synthetic_day_0/')
        report=request(m,csrf,'/focus-calendar/report');assert report['counts']['contacts_recorded']>=2
        with synthetic_db() as sql:
            rows=sql.execute("SELECT kind,count(*) FROM activities WHERE salon_id=ANY(%s) AND kind IN ('sales_draft','instagram_manual','instagram_reply_manual','sales_refused') GROUP BY kind",([s['id'] for s in salons],)).fetchall()
            assert dict(rows)=={'sales_draft':3,'instagram_manual':2,'instagram_reply_manual':1,'sales_refused':1}
            assert sql.execute("SELECT count(*) FROM activities WHERE salon_id=ANY(%s) AND kind='instagram_manual' AND (body::jsonb->>'api_confirmed_sent')::boolean",([s['id'] for s in salons],)).fetchone()[0]==0
        manifest=request(m,csrf,'/health') # PII-free readiness only, not production.
        cache=page.evaluate('''async()=>{let result=[];for(const key of await caches.keys()){for(const r of await (await caches.open(key)).keys())result.push(r.url)}return result}''')
        assert all(u.endswith('/offline.html') for u in cache)
        Path('test-results').mkdir(exist_ok=True);page.screenshot(path='test-results/sales-day-'+label+'.png')
        assert not browser_external, 'External browser request detected'
        attempts=Path(os.environ['FOCUS_TEST_EXTERNAL_ATTEMPTS'])
        assert not attempts.exists(), 'External backend request detected'
        results.append({'service_worker':'blocked_for_fault_injection; tested separately by production_browser_check','negative_control':probe,'engine':label,'expired_unsent_draft_renewed':True,'old_draft_preserved':True,'synthetic_salons':10,'duplicate_rejected':True,'manual_sent_declarations':2,'positive_reply':1,'refusal':1,'inbound_fixture_deduplicated':True,'outbound_http_calls':0,'kpi':report['counts'],'passed':True})
        m.close();rep.close();browser.close()
Path('test-results/sales-day.json').write_text(json.dumps(results,indent=2))
print('Sales day acceptance: Chromium + WebKit PASS (synthetic only, no DM)')
