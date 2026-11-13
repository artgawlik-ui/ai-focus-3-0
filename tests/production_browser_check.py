"""Real HTTPS browser checks in Chromium desktop and WebKit with iPhone emulation."""
import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
origin=os.getenv('FOCUS_TEST_ORIGIN','https://ai-focus-3-0.onrender.com')
isolated=origin.startswith('http://127.0.0.1:')
credentials=json.loads(Path(os.getenv('FOCUS_TEST_CREDENTIAL_FILE','.render-auth/verification.json')).read_text())

def open_mobile_menu(page, target, diagnostic_name):
    """Open, rather than toggle, the mobile menu and verify its target is reachable."""
    sidebar = page.locator('.sidebar')
    try:
        if 'open' not in (sidebar.get_attribute('class') or '').split():
            page.get_by_label('Otwórz menu', exact=True).click()
        expect(sidebar).to_have_class('sidebar open', timeout=30000)
        expect(target).to_be_in_viewport(timeout=30000)
    except Exception:
        output = Path('test-results')
        output.mkdir(exist_ok=True)
        # Geometry only: do not capture CRM text, credentials or storage contents.
        geometry = page.evaluate("""() => {
            const rect = element => {
                if (!element) return null;
                const r = element.getBoundingClientRect();
                return {x:r.x,y:r.y,width:r.width,height:r.height};
            };
            const sidebar = document.querySelector('.sidebar');
            const target = document.querySelector('.sidebar .settings');
            return {
                viewport:{width:innerWidth,height:innerHeight},
                sidebar:{className:sidebar?.className,rect:rect(sidebar),
                         transform:sidebar ? getComputedStyle(sidebar).transform : null},
                settings:rect(target)
            };
        }""")
        (output / (diagnostic_name + '-menu-geometry.json')).write_text(
            json.dumps(geometry, indent=2))
        page.screenshot(path=str(output / (diagnostic_name + '-menu-failure.png')),
                        full_page=True)
        raise

results=[]
with sync_playwright() as p:
    cases=[('chromium-desktop',p.chromium,{'viewport':{'width':1440,'height':1050}},os.getenv('FOCUS_TEST_CHROMIUM_EXECUTABLE','/usr/bin/chromium')),('webkit-iphone',p.webkit,p.devices['iPhone 13'],os.getenv('FOCUS_TEST_WEBKIT_EXECUTABLE','/workspace/ai-focus-3-0/.tools/run-webkit.sh'))]
    repeats = int(os.getenv('FOCUS_TEST_WEBKIT_REPETITIONS', '1'))
    if not 1 <= repeats <= 10:
        raise ValueError('FOCUS_TEST_WEBKIT_REPETITIONS must be between 1 and 10')
    if repeats > 1 and not isolated:
        raise ValueError('Repeated browser checks require an isolated local origin')
    cases = cases[:1] + cases[1:] * repeats
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
        if label=='webkit-iphone':open_mobile_menu(page, page.get_by_role('button',name='Baza salonów',exact=True), label+'-nav-1')
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
            if label=='webkit-iphone':open_mobile_menu(page, page.get_by_role('button',name='Agent sprzedaży',exact=False), label+'-nav-2')
            page.get_by_role('button',name='Agent sprzedaży',exact=False).click()
            page.locator('select[name="salon_id"]').select_option(label='[TEST TECHNICZNY] Ai Focus 3.0 · Głogów')
            page.get_by_role('button',name='Zleć analizę i szkic').click()
            page.get_by_text('Proponowany priorytet:',exact=True).first.wait_for(timeout=20000)
            page.get_by_text('Kolejny krok:',exact=True).first.wait_for()
            page.get_by_text('Źródła analizy',exact=False).first.wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if isolated and os.getenv('META_ENABLED')=='true':
            if label=='webkit-iphone':open_mobile_menu(page, page.get_by_role('button',name='Ustawienia i integracje',exact=True), label+'-nav-3')
            page.get_by_role('button',name='Ustawienia i integracje',exact=True).click()
            page.get_by_role('heading',name='Instagram — status i rozmowy').wait_for()
            page.get_by_label('Konwersacja Instagram',exact=True).select_option(index=1)
            page.get_by_label('Szkic Instagram',exact=True).fill('Syntetyczny szkic wizyty 15–20 minut. Bez wysyłki.')
            page.get_by_role('button',name='Zapisz szkic · bez wysyłki').click()
            page.get_by_role('button',name='Zatwierdź szkic · bez wysyłki').first.click()
            page.get_by_text('Zatwierdzona · niewysłana',exact=False).first.wait_for()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        if label=='webkit-iphone':open_mobile_menu(page, page.get_by_label('Wyloguj',exact=True), label+'-nav-4')
        page.get_by_label('Wyloguj',exact=True).click()
        page.get_by_role('heading',name='Zaloguj się do Ai Focus').wait_for()
        assert page.request.get(origin+'/api/salons').status==401
        assert not errors,errors
        results.append({'browser':label,'login':True,'logout':True,'private_data_not_in_service_worker_cache':True,'crm_read':True,'crm_write_on_isolated_copy':isolated,'no_horizontal_scroll':True,'pwa_manifest_icons':True,'apple_standalone_meta':True,'service_worker_offline_fallback':True,'javascript_errors':errors})
        context.close();browser.close();print(label+': PASS')
Path('test-results/production-browser-check.json').write_text(json.dumps(results,indent=2))
