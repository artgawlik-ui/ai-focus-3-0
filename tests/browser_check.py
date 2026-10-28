"""Actual browser smoke checks at desktop and iPhone viewports."""
import json, uuid, os
from pathlib import Path
from playwright.sync_api import sync_playwright
origin=os.getenv('FOCUS_TEST_ORIGIN','http://127.0.0.1:8001')
out=Path('test-results');out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for label,viewport in [('desktop',{'width':1440,'height':1100}),('iphone',{'width':390,'height':844})]:
        context=browser.new_context(viewport=viewport,is_mobile=label=='iphone',has_touch=label=='iphone')
        page=context.new_page(); errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(origin);page.get_by_label('Adres e-mail').fill('e2e@focus.test');page.get_by_label('Hasło',exact=True).fill('E2eSyntheticPassword123!');page.get_by_role('button',name='Wejdź do swojej przestrzeni').click()
        page.get_by_role('heading',name='Dzień dobry, Tester.').wait_for()
        page.get_by_text('Salon Testowy Atelier',exact=True).wait_for()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),label+' dashboard overflow'
        page.screenshot(path=str(out/(label+'-dashboard.png')),full_page=True)
        if label=='iphone':page.get_by_label('Otwórz menu').click()
        page.get_by_role('button',name='Baza salonów',exact=True).click()
        page.get_by_label('Szukaj salonu').fill('Atelier')
        page.get_by_text('Salon Testowy Atelier',exact=True).click()
        page.get_by_role('dialog').wait_for()
        assert page.get_by_role('heading',name='Historia relacji').count()==1
        page.get_by_label('Zamknij',exact=True).click()
        page.get_by_role('button',name='Dodaj salon',exact=True).click()
        page.get_by_label('Nazwa salonu',exact=True).fill('Salon E2E '+label+' '+uuid.uuid4().hex[:6])
        page.get_by_label('Miasto',exact=True).fill('Głogów')
        page.get_by_role('button',name='Zapisz salon').click()
        page.get_by_role('status').filter(has_text='Salon został zapisany').wait_for()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),label+' CRM overflow'
        page.screenshot(path=str(out/(label+'-crm.png')),full_page=True)
        manifest=page.request.get(origin+'/manifest.webmanifest').json()
        assert manifest['display']=='standalone'
        for icon in manifest['icons']:assert page.request.get(origin+icon['src']).status==200
        assert page.request.get(origin+'/sw.js').status==200
        assert not errors,errors
        print(label+': login, dashboard, CRM read/write, mobile overflow, manifest and icons passed')
        context.close()
    browser.close()
