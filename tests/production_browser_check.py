"""Real HTTPS browser checks in Chromium desktop and WebKit with iPhone emulation."""
import json, os
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode
from playwright.sync_api import sync_playwright
from scripts.local_test_policy import local_origin
origin=local_origin()
isolated=origin.startswith('http://127.0.0.1:')
credentials=json.loads(Path(os.environ['FOCUS_TEST_CREDENTIAL_FILE']).read_text())
results=[]
with sync_playwright() as p:
    cases=[('chromium-desktop',p.chromium,{'viewport':{'width':1440,'height':1050}},os.getenv('FOCUS_TEST_CHROMIUM_EXECUTABLE','/usr/bin/chromium')),('webkit-iphone',p.webkit,p.devices['iPhone 13'],os.getenv('FOCUS_TEST_WEBKIT_EXECUTABLE','/workspace/ai-focus-3-0/.tools/run-webkit.sh'))]
    for label,engine,options,executable in cases:
        browser=engine.launch(executable_path=executable if Path(executable).exists() else None,headless=True,args=['--no-sandbox'] if label.startswith('chromium') else [])
        context=browser.new_context(**options)
        page=context.new_page();errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.goto(origin);page.get_by_label('Adres e-mail').fill(credentials['email']);page.get_by_label('Hasło',exact=True).fill(credentials['password']);page.get_by_role('button',name='Wejdź do swojej przestrzeni').click()
        page.get_by_role('heading',name='Dzień dobry, Weryfikacja.').wait_for()
        page.get_by_role('heading',name='Przegląd sprzedaży').wait_for()
        page.get_by_text('Salony w bazie',exact=True).wait_for()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path='test-results/'+label+'-production-dashboard.png',full_page=True)
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
            page.get_by_label('Data planu',exact=True).fill('2027-03-29')
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
            page.get_by_role('heading',name='Instagram — status i rozmowy').wait_for()
            page.get_by_label('Konwersacja Instagram',exact=True).select_option(index=1)
            page.get_by_label('Szkic Instagram',exact=True).fill('Syntetyczny szkic wizyty 15–20 minut. Bez wysyłki.')
            page.get_by_role('button',name='Zapisz szkic · bez wysyłki').click()
            page.get_by_role('button',name='Zatwierdź szkic · bez wysyłki').first.click()
            page.get_by_text('Zatwierdzona · niewysłana',exact=False).first.wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if isolated:
            section=page.get_by_label('Google Calendar integracja',exact=True)
            section.get_by_role('button',name='Przygotuj połączenie Google',exact=True).click()
            link=section.get_by_role('link',name='Otwórz autoryzację Google',exact=True)
            link.wait_for();params=parse_qs(urlsplit(link.get_attribute('href')).query)
            assert params['code_challenge_method']==['S256']
            # Local callback only. Provider exchange is a strict synthetic transport fixture.
            page.request.get(origin+'/api/google-calendar/oauth/callback?'+urlencode({'state':params['state'][0],'code':'synthetic-'+label}))
            section.get_by_role('button',name='Odśwież status Google',exact=True).click()
            section.get_by_role('button',name='Zatwierdź konto handlowca',exact=True).click()
            section.get_by_role('button',name='Utwórz dedykowany kalendarz',exact=True).click()
            token=page.request.get(origin+'/api/auth/me').json()['csrf']
            visit=next(v for v in page.request.get(origin+'/api/appointments').json() if v['salon_name']=='[TEST] Salon promień '+label)
            assert page.request.patch(origin+'/api/appointments/'+visit['id'],data={'status':'confirmed','confirmation_recorded':True},headers={'X-CSRF-Token':token}).status==200
            section.get_by_role('button',name='Odśwież status Google',exact=True).click()
            section.get_by_label('Wizyta do synchronizacji',exact=True).select_option(visit['id'])
            section.get_by_role('button',name='Odśwież podgląd wizyty',exact=True).click()
            section.get_by_label('Zatwierdzam wysłanie tej wersji wizyty do Google',exact=True).check()
            previous=[j['id'] for j in page.request.get(origin+'/api/google-calendar/requests').json()]
            section.get_by_role('button',name='Zleć zatwierdzoną synchronizację',exact=True).click()
            page.wait_for_function('''async data=>{const rows=await(await fetch('/api/google-calendar/requests')).json();return rows.some(j=>j.appointment_id===data.visit&&!data.previous.includes(j.id)&&j.status==='synced')}''',arg={'visit':visit['id'],'previous':previous},timeout=25000)
            section.get_by_role('button',name='Odśwież status Google',exact=True).click()
            history=section.locator('article').filter(has=page.get_by_text('[TEST] Salon promień '+label,exact=True)).first
            history.get_by_text('Stan potwierdzony przez API',exact=False).wait_for(timeout=25000)
            assert page.request.patch(origin+'/api/appointments/'+visit['id'],data={'status':'cancelled'},headers={'X-CSRF-Token':token}).status==200
            section.get_by_role('button',name='Odśwież status Google',exact=True).click()
            section.get_by_label('Wizyta do synchronizacji',exact=True).select_option(visit['id'])
            section.get_by_role('button',name='Odśwież podgląd wizyty',exact=True).click()
            section.get_by_label('Zatwierdzam wysłanie tej wersji wizyty do Google',exact=True).check()
            previous=[j['id'] for j in page.request.get(origin+'/api/google-calendar/requests').json()]
            section.get_by_role('button',name='Zleć zatwierdzoną synchronizację',exact=True).click()
            page.wait_for_function('''async data=>{const rows=await(await fetch('/api/google-calendar/requests')).json();return rows.some(j=>j.appointment_id===data.visit&&!data.previous.includes(j.id)&&j.status==='synced')}''',arg={'visit':visit['id'],'previous':previous},timeout=25000)
            section.get_by_role('button',name='Odśwież status Google',exact=True).click()
            history.get_by_text('Stan potwierdzony przez API',exact=False).wait_for(timeout=25000)
            section.get_by_role('button',name='Odłącz Google od aplikacji',exact=True).click()
            section.get_by_text('Brak połączonego konta.',exact=False).wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if label=='webkit-iphone':page.get_by_label('Otwórz menu').click()
        page.get_by_label('Wyloguj',exact=True).click()
        page.get_by_role('heading',name='Zaloguj się do Ai Focus').wait_for()
        assert page.request.get(origin+'/api/salons').status==401
        assert not errors,errors
        results.append({'browser':label,'login':True,'logout':True,'private_data_not_in_service_worker_cache':True,'crm_read':True,'crm_write_on_isolated_copy':isolated,'no_horizontal_scroll':True,'pwa_manifest_icons':True,'apple_standalone_meta':True,'service_worker_offline_fallback':True,'javascript_errors':errors})
        context.close();browser.close();print(label+': PASS')
Path('test-results/production-browser-check.json').write_text(json.dumps(results,indent=2))
