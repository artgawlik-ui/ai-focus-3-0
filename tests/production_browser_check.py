"""Real HTTPS browser checks in Chromium desktop and WebKit with iPhone emulation."""
import json, os, time
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode
from playwright.sync_api import sync_playwright,expect
from scripts.local_test_policy import local_origin
from tests.browser_capture import capture_page,screenshot_probe
origin=local_origin()
isolated=origin.startswith('http://127.0.0.1:')
credentials=json.loads(Path(os.environ['FOCUS_TEST_CREDENTIAL_FILE']).read_text())
results=[]
with sync_playwright() as p:
    cases=[('chromium-desktop',p.chromium,{'viewport':{'width':1440,'height':1050}},os.getenv('FOCUS_TEST_CHROMIUM_EXECUTABLE','/usr/bin/chromium')),('webkit-iphone',p.webkit,p.devices['iPhone 13'],os.getenv('FOCUS_TEST_WEBKIT_EXECUTABLE','/workspace/ai-focus-3-0/.tools/run-webkit.sh'))]
    if isolated and not os.getenv('CI') and os.getenv('FOCUS_TEST_LOCAL_CHROMIUM_ONLY')=='true':cases=cases[:1]
    for label,engine,options,executable in cases:
        browser=engine.launch(executable_path=executable if Path(executable).exists() else None,headless=True,args=['--no-sandbox'] if label.startswith('chromium') else [])
        context=browser.new_context(**options)
        capture_regression=screenshot_probe(context,label,'test-results')
        page=context.new_page();errors=[];native_metrics={}
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.goto(origin);page.get_by_label('Adres e-mail').fill(credentials['email']);page.get_by_label('Hasło',exact=True).fill(credentials['password']);page.get_by_role('button',name='Wejdź do swojej przestrzeni').click()
        page.get_by_role('heading',name='Dzień dobry, Weryfikacja.').wait_for()
        page.get_by_role('heading',name='Przegląd sprzedaży').wait_for()
        page.get_by_text('Salony w bazie',exact=True).wait_for()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if isolated:
            page.get_by_label('Centrum pracy Focus',exact=True).get_by_role('heading',name='Zadania i wynik kontaktu',exact=True).wait_for()
            expect(page.locator('[aria-busy=true]')).to_have_count(0)
        dashboard_capture=capture_page(page,'test-results/'+label+'-production-dashboard.png')
        if label=='webkit-iphone':page.get_by_label('Otwórz menu').click()
        page.get_by_role('button',name='Baza salonów',exact=True).click()
        page.get_by_label('Szukaj salonu').fill('[TEST TECHNICZNY]')
        page.get_by_text('[TEST TECHNICZNY] Ai Focus 3.0',exact=True).click()
        page.get_by_role('dialog').wait_for();assert page.get_by_role('heading',name='Historia relacji').count()==1
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if isolated:
            page.get_by_role('button',name='Edytuj profil').click()
            page.get_by_label('Osoba kontaktowa',exact=True).fill('Weryfikacja techniczna')
            page.get_by_role('button',name='Zapisz salon').click();page.get_by_role('status').filter(has_text='Salon został zapisany').wait_for()
        else:
            page.get_by_label('Zamknij',exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        manifest=page.request.get(origin+'/manifest.webmanifest').json();assert manifest['display']=='standalone' and manifest['start_url']=='/'
        for icon in manifest['icons']:assert page.request.get(origin+icon['src']).status==200
        assert page.locator('meta[name="apple-mobile-web-app-capable"]').get_attribute('content')=='yes'
        page.evaluate('navigator.serviceWorker.ready')
        assert page.evaluate('navigator.serviceWorker.controller !== null')
        network_flag=os.getenv('FOCUS_TEST_OFFLINE_FLAG') if label=='webkit-iphone' else None
        if network_flag: Path(network_flag).touch()
        else: context.set_offline(True)
        try:
            try: page.reload(wait_until='domcontentloaded')
            except Exception:
                if label!='webkit-iphone': raise
            page.get_by_role('heading',name='Jesteś offline').wait_for()
        finally:
            if network_flag: Path(network_flag).unlink(missing_ok=True)
            else: context.set_offline(False)
        page.goto(origin);page.get_by_role('heading',name='Dzień dobry, Weryfikacja.').wait_for()
        cache_urls=page.evaluate('''async()=>{const urls=[];for(const name of await caches.keys()){const cache=await caches.open(name);for(const request of await cache.keys())urls.push(request.url);}return urls;}''')
        assert cache_urls and all(url.endswith('/offline.html') for url in cache_urls),cache_urls
        if isolated:
            if label=='webkit-iphone':page.get_by_label('Otwórz menu').click()
            page.get_by_role('button',name='Agent sprzedaży',exact=False).click()
            page.get_by_label('Miasto',exact=True).fill('Głogów')
            page.get_by_role('button',name='Znajdź miejscowość',exact=True).click()
            page.get_by_label('Miejscowość i centrum').select_option(index=1)
            page.get_by_label('Promień (km)').fill('10')
            page.get_by_role('button',name='Szukaj w promieniu',exact=True).click()
            page.get_by_text('[TEST] Salon promień',exact=True).wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.get_by_role('button',name='Sprawdź i dodaj [TEST] Salon promień',exact=True).click()
            page.get_by_role('dialog').wait_for()
            assert page.get_by_label('Nazwa salonu',exact=True).input_value()=='[TEST] Salon promień'
            page.get_by_label('Nazwa salonu',exact=True).fill('[TEST] Salon promień '+label)
            page.get_by_role('button',name='Zapisz salon',exact=True).click()
            page.get_by_role('status').filter(has_text='Salon został zapisany').wait_for()
            if label=='webkit-iphone':page.get_by_label('Otwórz menu').click()
            page.get_by_role('button',name='Kalendarz i trasy',exact=True).click()
            plan_day=page.get_by_label('Data planu',exact=True)
            plan_day.fill('2027-03-29')
            plan_day.press('Tab')
            expect(plan_day).to_have_value('2027-03-29')
            page.get_by_role('button',name='Zaproponuj wizytę',exact=True).click()
            dialog=page.get_by_role('dialog')
            dialog.locator('select[name="salon_id"]').select_option(label='[TEST] Salon promień '+label+' · Głogów')
            assert dialog.get_by_label('Czas trwania (minuty)',exact=True).input_value()=='20'
            hour='10' if label.startswith('chromium') else '12'
            dialog.get_by_label('Termin (strefa urządzenia)',exact=True).fill('2027-03-29T'+hour+':00')
            dialog.get_by_role('button',name='Zapisz wizytę',exact=True).click()
            page.get_by_role('status').filter(has_text='Plan wizyt został zapisany').wait_for()
            card=page.locator('.visit-card').filter(has=page.get_by_role('heading',name='[TEST] Salon promień '+label,exact=True))
            card.get_by_text('Propozycja',exact=True).wait_for()
            assert card.get_by_role('link',name='Nawiguj do sprawdzonego adresu').count()==0
            card.get_by_role('button',name='Profil i historia',exact=True).click()
            page.get_by_role('heading',name='Historia relacji',exact=True).wait_for()
            page.get_by_label('Sprawdziłem aktualny adres salonu',exact=True).check()
            page.get_by_role('button',name='Potwierdź adres do nawigacji',exact=True).click()
            page.get_by_role('status').filter(has_text='Adres ręcznie potwierdzony').wait_for()
            page.get_by_label('Zamknij',exact=True).click()
            card.get_by_role('link',name='Nawiguj do sprawdzonego adresu').wait_for()
            card.get_by_role('button',name='Zmień wizytę',exact=True).click()
            dialog=page.get_by_role('dialog')
            dialog.get_by_label('Termin (strefa urządzenia)',exact=True).fill('2027-03-29T'+hour+':30')
            dialog.get_by_label('Czas trwania (minuty)',exact=True).fill('15')
            dialog.get_by_label('Status wizyty',exact=True).select_option('confirmed')
            dialog.get_by_label('Klient uzgodnił termin',exact=False).check()
            dialog.get_by_role('button',name='Zapisz wizytę',exact=True).click()
            card.get_by_text('Potwierdzona',exact=True).wait_for()
            card.get_by_role('button',name='Odwołaj wizytę',exact=True).click()
            card.get_by_text('Anulowana',exact=True).wait_for()
            page.get_by_label('Widok planu',exact=True).select_option('7')
            page.get_by_label('Handlowiec',exact=True).select_option('ci-manager')
            card.get_by_text('Anulowana',exact=True).wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            if label=='webkit-iphone':page.get_by_label('Otwórz menu').click()
            page.get_by_role('button',name='Agent sprzedaży',exact=False).click()
            page.locator('select[name="salon_id"]').select_option(label='[TEST TECHNICZNY] Ai Focus 3.0 · Głogów')
            page.get_by_role('button',name='Zleć analizę i szkic').click()
            page.get_by_text('Proponowany priorytet:',exact=True).first.wait_for(timeout=20000)
            page.get_by_text('Kolejny krok:',exact=True).first.wait_for()
            page.get_by_text('Źródła analizy',exact=False).first.wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if isolated and os.getenv('META_ENABLED')=='true':
            if label=='webkit-iphone':page.get_by_label('Otwórz menu').click()
            page.get_by_role('button',name='Ustawienia i integracje',exact=True).click()
            operations=page.get_by_label('Diagnostyka kolejki Focus',exact=True)
            # Require a successful read, rather than masking a missing response with retries.
            with page.expect_response(lambda response:response.url==origin+'/api/focus-calendar/diagnostics') as diagnostic_response:
                operations.get_by_role('button',name='Odczytaj stan kolejki',exact=True).click()
            assert diagnostic_response.value.status==200, 'Diagnostics read failed'
            expect(operations.get_by_text('Świeży sygnał procesu nie potwierdza wykonania przypomnień.',exact=False)).to_be_visible()
            # A queued job with an invalid timestamp is not an empty queue.
            fault=Path(os.environ['FOCUS_TEST_INVALID_QUEUE_TIME_FLAG'])
            fault.touch()
            try:
                operations.get_by_role('button',name='Odczytaj stan kolejki',exact=True).click()
                operations.get_by_text('Wiek najstarszego oczekującego zadania agenta: brak wiarygodnej daty.',exact=True).wait_for()
            finally:fault.unlink(missing_ok=True)
            operations.get_by_role('button',name='Pokaż podgląd retencji',exact=True).click()
            operations.get_by_text('Kasowanie nie jest dostępne.',exact=False).wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.get_by_role('heading',name='Instagram — status i rozmowy').wait_for()
            page.get_by_label('Konwersacja Instagram',exact=True).select_option(index=1)
            page.get_by_label('Szkic Instagram',exact=True).fill('Syntetyczny szkic wizyty 15–20 minut. Bez wysyłki.')
            page.get_by_role('button',name='Zapisz szkic · bez wysyłki').click()
            page.get_by_role('button',name='Zatwierdź szkic · bez wysyłki').first.click()
            page.get_by_text('Zatwierdzona · niewysłana',exact=False).first.wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if isolated:
            # Native planner replaces the retired Google UI; Google unit guards remain.
            if label=='webkit-iphone':page.get_by_label('Otwórz menu').click()
            page.get_by_role('button',name='Kalendarz i trasy',exact=True).click()
            section=page.get_by_label('Centrum pracy Focus',exact=True)
            section.get_by_role('button',name='Przygotuj zadania na dziś',exact=True).click()
            section.get_by_role('heading',name='Zadania i wynik kontaktu',exact=True).wait_for()
            assert page.request.get(origin+'/api/focus-calendar/contacts').status==200
            assert page.request.get(origin+'/api/focus-calendar/tasks').json()
            # The second engine inherits 45 higher-priority tasks. Search the new
            # task explicitly rather than assuming it belongs to the first page.
            section.get_by_label('Szukaj w planie',exact=True).fill('Syntetyczne zadanie '+label)
            section.get_by_label('Strony zadań',exact=True).get_by_text('0 / 0',exact=True).wait_for()
            section.get_by_label('Tytuł zadania',exact=True).fill('Syntetyczne zadanie '+label)
            section.get_by_label('Termin zadania — Warszawa',exact=True).fill('2027-03-20T10:00')
            section.get_by_role('button',name='Dodaj zadanie',exact=True).click()
            section.get_by_text('Syntetyczne zadanie '+label,exact=True).wait_for()
            card=section.locator('article').filter(has_text='Syntetyczne zadanie '+label)
            card.get_by_label('Wynik działania',exact=True).fill('Syntetyczna rozmowa zarejestrowana przez test')
            card.get_by_label('Czy rzeczywiście odbył się kontakt?',exact=True).select_option('call')
            card.get_by_role('button',name='Zapisz wynik zadania',exact=True).click()
            card.get_by_text('Zakończone',exact=False).wait_for()
            saved=next(t for t in page.request.get(origin+'/api/focus-calendar/tasks').json() if t['title']=='Syntetyczne zadanie '+label)
            assert saved['status']=='completed'
            contact=next(r for r in page.request.get(origin+'/api/focus-calendar/contacts').json() if r['salon_id']==saved['salon_id'])
            assert contact['last_contact_at'] and contact['days_since_contact']==0
            section.get_by_text('Indywidualny okres każdego klienta',exact=True).click()
            section.get_by_label('Klient — okres kontaktu',exact=True).select_option(saved['salon_id'])
            section.get_by_label('Liczba dni między kontaktami',exact=True).fill('21')
            section.get_by_role('button',name='Zapisz indywidualny okres',exact=True).click()
            page.wait_for_function("""async id=>{const rows=await(await fetch('/api/focus-calendar/contacts')).json();return rows.some(r=>r.salon_id===id&&r.interval_days===21)}""",arg=saved['salon_id'])
            token=page.request.get(origin+'/api/auth/me').json()['csrf']
            for index in range(45):
                response=page.request.post(origin+'/api/focus-calendar/tasks',headers={'X-CSRF-Token':token},data={'salon_id':saved['salon_id'],'title':'[PAGE] '+label+' '+str(index).zfill(2),'due_at':'2027-04-10T09:00:00Z'})
                assert response.status==201
            started=time.perf_counter()
            section.get_by_label('Szukaj w planie',exact=True).fill('[PAGE] '+label)
            page.wait_for_function("""prefix=>Array.from(document.querySelectorAll('[aria-label="Centrum pracy Focus"] article strong')).filter(n=>n.textContent.startsWith(prefix)).length===20""",arg='[PAGE] '+label)
            native_metrics['search_first_page_ms']=round((time.perf_counter()-started)*1000,2)
            first=section.locator('article strong').all_text_contents()
            started=time.perf_counter();button=section.get_by_role('button',name='Następna strona zadań',exact=True)
            if label=='webkit-iphone':button.tap()
            else:button.click()
            page.wait_for_function("""old=>{const titles=Array.from(document.querySelectorAll('[aria-label="Centrum pracy Focus"] article strong')).map(n=>n.textContent);return titles.length===20&&!titles.includes(old[0])}""",arg=first)
            second=section.locator('article strong').all_text_contents()
            assert not set(first)&set(second)
            native_metrics['next_page_ms']=round((time.perf_counter()-started)*1000,2)
            section.get_by_label('Filtr statusu zadania',exact=True).select_option('completed')
            section.get_by_label('Strony zadań',exact=True).get_by_text('0 / 0',exact=True).wait_for()
            native_metrics['page_size']=20;native_metrics['records_in_test']=45
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if label=='webkit-iphone':page.get_by_label('Otwórz menu').click()
        page.get_by_label('Wyloguj',exact=True).click()
        page.get_by_role('heading',name='Zaloguj się do Ai Focus').wait_for()
        assert page.request.get(origin+'/api/salons').status==401
        assert not errors,errors
        results.append({'browser':label,'login':True,'logout':True,'private_data_not_in_service_worker_cache':True,'crm_read':True,'crm_write_on_isolated_copy':isolated,'no_horizontal_scroll':True,'pwa_manifest_icons':True,'apple_standalone_meta':True,'service_worker_offline_fallback':True,'javascript_errors':errors,'native_pagination':native_metrics,'capture_regression':capture_regression,'dashboard_capture_tiles':len(dashboard_capture['tiles'])})
        context.close();browser.close();print(label+': PASS '+json.dumps({'native_pagination':native_metrics,'capture_regression':capture_regression,'dashboard_capture_tiles':len(dashboard_capture['tiles'])}))
Path('test-results/production-browser-check.json').write_text(json.dumps(results,indent=2))
