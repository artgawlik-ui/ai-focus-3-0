# Ai Focus 3.0.2 — wdrożenie Unified Login, 2026-10-31

**Kod wdrożony i zweryfikowany. Integracja Meta jest wyłączona i nie jest jeszcze rzeczywistym połączeniem z Instagramem. Żadnych rzeczywistych wiadomości nie wysłano.**

Produkcja: https://ai-focus-3-0.onrender.com . Render live: `dep-dbj59qff3r2c73f077u0`, commit **cd22a44415732a1e25b558bfec38cf498115b90f**, zakończony 20:52:37 UTC. Wersja API 3.0.2. Późniejsze zmiany dokumentacji nie zmieniają uruchomionego commita. Bazą pozostaje `ai-focus-3-0-db`, `dpg-dbh1b0gm7kps73f0p2m0-a`, available, zewnętrzna allowlista pusta. Nie utworzono usług ani bazy i nie zmieniono planu.

## Właściwa ścieżka Meta

Configuration ID 2380634476006078 i nazwa Unified Login odpowiadają **Instagram API with Unified Login**, zbudowanej na **Facebook Login for Business**. Implementacja używa Meta App ID/Secret, config_id i **graph.facebook.com/v26.0**, nie Instagram App ID/Secret ani graph.instagram.com. Sam Configuration ID nie potwierdza zawartości konfiguracji, rodzaju konta, biznesowej weryfikacji ani uprawnień — do tego brakuje autoryzacji właściciela.

Token SUAT otrzymujemy przez serwerową wymianę kodu. Jego ważność zależy od konfiguracji Meta; nie stosujemy niewłaściwych ig_exchange_token/ig_refresh_token. Minimalne uprawnienia: **instagram_basic** (udostępnione konta) i **instagram_manage_messages** (komunikacja). Nie żądamy reklam, publikacji ani business_management. Dlatego plan obejmuje kontrolę ważności co dobę i ponowny OAuth przed wygaśnięciem, a nie automatyczną rotację przez szerokie Token Management API. Dane konta pochodzą z /me/assigned_instagram_accounts; /me dostarcza client_business_id/system-user, nie profil Instagram.

Aktualne wymagania, menu panelu, ograniczenia, źródła i data odczytu: [SETUP.md](SETUP.md).

## Zrobione i przetestowane

- OAuth właściciela: state 10 minut, nonce Secure/HttpOnly/SameSite=Lax, powiązanie z aktywną sesją CRM, jednorazowe state i hash kodu, obsługa error/error_reason, usuwanie końcówki #_, serwerowa wymiana kodu. Oryginalna sesja CRM pozostaje SameSite=Strict. Brak tokenów dostępu w odpowiedziach i logach testowych.
- Tokeny i treści rozmów szyfrowane w PostgreSQL; klucz wyłącznie w środowisku. Kontrola app_id, typu tokenu, minimalnych uprawnień i dozwolonego konta testowego. Odłączenie usuwa lokalny token i blokuje ingest, nie udaje zdalnego cofnięcia grantów Meta.
- Osobny webhook: GET challenge/verify token, POST X-Hub-Signature-256, limit ciała, transakcyjne zapisy i deduplikacja po ID wiadomości/konwersacji. Podpisane usunięcie nie może zostać cofnięte spóźnionym duplikatem. Subskrypcja tylko messages; brak automatycznych odpowiedzi i transportu wysyłki.
- Ręczne przypisanie rozmowy do salonu, historia ze źródłem, dostęp tylko do przypisanych klientów dla handlowca. Rozróżnione draft, approved, manual_sent, api_confirmed_sent, received i deleted. Dostarczenie/odczyt nie są zgadywane ani zaimplementowane jako potwierdzone statusy.
- Panel statusu, autoryzacji konta testowego, sprawdzania ważności, odłączenia, rozmów i szkiców. Właściciel zatwierdza szkic; manual_sent oznacza jego oświadczenie o wysyłce ręcznej, nie dowód API.
- Agent odczytuje potwierdzone odpowiedzi i wskazuje źródła. Szkic przedstawia reprezentanta NAK Hair/muk Haircare i proponuje wizytę 15–20 minut, bez oferty produktów i cen. Nie tworzy wizyt i nie wysyła wiadomości.
- Podpisane callbacki deauthorize/data deletion, idempotentny rejestr żądań i publiczny status bez danych klienta. Odłączenie nie jest oznaczane jako usunięcie treści. Nieznana tożsamość, dane CRM i kopie wymagają przeglądu administratora; nie twierdzimy, że całość żądania RODO została automatycznie zakończona.
- Retencja: brak ujawniania treści starszej niż 30 dni, fizyczne czyszczenie co godzinę, ID wiadomości do 90 dni. Czyszczenie działa również przy wyłączonej integracji. Zła konfiguracja Meta nie blokuje podstawowej kolejki CRM. Naprawiono zamykanie mobilnego menu po wejściu do ustawień.

## Wyniki testów i dowody

| Kontrola | Wynik / dowód |
|---|---|
| Backend i integracja na syntetycznej PostgreSQL | `DATABASE_URL=<lokalna focus3_test> python -m pytest -q`: **49 passed**, 0 failures/errors; meta-full.xml / evidence/meta-tests-summary.json |
| Kompilacja | `npm run build --prefix frontend`: PASS, TypeScript + Vite 6.4.5 |
| E2E syntetyczne | `python -m tests.ci_e2e`: Chromium desktop i WebKit/iPhone 13 PASS, w tym szkic i zatwierdzenie bez wysyłki |
| Audyt Python | `pip-audit -r requirements.txt`: **0 znanych podatności** |
| Audyt frontend | `npm audit --prefix frontend`: **0 podatności** |
| Repozytorium | Skan 15 zmienionych plików: 0 dopasowań sprawdzanych wzorców sekretów; .render-auth nie jest śledzony |
| Kopia i migracja | Świeży zaszyfrowany pg_dump → lokalne odtworzenie → 9 tabel CRM bez zmian → 5 pustych tabel; `alembic check`: brak różnic |
| Kopia przed końcową korektą | Odtworzenie wszystkich **15 tabel**, zgodność liczebności i SHA-256, brak nowej migracji |
| Produkcyjne HTTPS/UI | Chromium i WebKit PASS, zero żądań modyfikujących, zero błędów JS, brak poziomego przewijania, cache tylko publiczny offline.html |
| Dane po końcowym wdrożeniu | **Wszystkie 15 liczebności i SHA-256 identyczne z końcowym punktem odniesienia**, po ponownym odczycie UI |
| Runtime | health 200 / 3.0.2, właściciel zalogowany, konto techniczne nieaktywne, anonimowe CRM/Meta status 401, logi błędów po wdrożeniu: 0 |

[Pełne CI końcowego commita — SUCCESS](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41240408027). [CI main tego samego kodu](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41240820174). [Pierwsze wydanie i migracja — SUCCESS](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41239548881). Dwa ostrzeżenia deprecacji narzędzi testowych pozostają, bez błędów i bez znanej podatności. Skan wzorców nie jest dowodem braku wszystkich możliwych sekretów.

Konta, klienci, historia i wizyty zachowane. Stan po wdrożeniu: salons 1, activities 8, appointments 1, jobs 3, users 2, sessions 5, login_attempts 0, trainings 0, integration_links 0, alembic_version 1; pięć tabel meta_* ma po 0 rekordów. Zmiana metadanych migracji 002→003 była planowana; żadna z dziewięciu starych tabel CRM nie zmieniła skrótu wskutek migracji. Końcowa korekta nie zmieniła żadnej z 15 tabel. Szczegóły: [evidence/final-integrity.json](evidence/final-integrity.json), [evidence/meta-production-check.json](evidence/meta-production-check.json).

Kopie i sekrety pozostają prywatne poza repozytorium; do raportu dołączono wyłącznie odfiltrowane wyniki. Testy zapisów prowadzono na syntetycznych bazach, migracje na odtworzonej kopii; kontrola produkcyjna po wdrożeniu była odczytowa.

## Wycofanie

Bezpośredni start starego df78fd7 na rewizji 003 nie rozpoznaje nowej migracji. Przygotowano zgodny wariant poprzedniego zachowania CRM: **4c2eedf7f934daa2fe7c2a860d3366d72860b649**, gałąź rollback/phase2-meta-schema, plus wyłącznie rejestracja dodatkowego schematu. [CI rollback — SUCCESS](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41239153730); start migratora na odtworzonej kopii nie zmienił jej skrótów. Nie wykonano produkcyjnego rollbacku ani kasowania tabel. Bezpośrednim wcześniejszym, zweryfikowanym wydaniem tej samej rewizji jest też 98ac75e / dep-dbj54fm7bikc73eep290.

## Niezweryfikowane / oczekujące na właściciela

**Nie wykonano rzeczywistego OAuth Meta ani testu na prawdziwym koncie testowym.** Meta credentials/conversations/messages mają 0 rekordów. Nie ma jeszcze potwierdzonej dostawy webhooka przez Meta, rzeczywistych grantów, czasu życia tokenu ani weryfikacji rodzaju @artur_uluru_hair. Testy transportu były atrapami oficjalnego API, nie kontaktem z Instagramem.

Wymagane są własny business portfolio, konto zawodowe Business/Creator, role aplikacji i odrębne profesjonalne konto testowe. Pozostawiamy Development; zwykłe Meta Test Users nie są obsługiwane według przewodnika Unified Login. Dokumentacja Webhooks Setup wymaga Live dla notyfikacji użytkowników, więc nie obiecujemy realnych rozmów w Development. Nie przełączano Live i nie składano App Review/Advanced Access ani Business Verification. Dla produkcji potrzebne będą wymagane przez Meta zgody i weryfikacje.

META_ENABLED pozostaje false, outbound zawsze false. Kod odrzuca autoryzację konta docelowego artur_uluru_hair w tym etapie testowym. Nie ma endpointu wysyłki i zatwierdzenie szkicu nie uruchamia transportu. Pierwszy DM pozostaje ręczny, po ocenie podstawy prawnej; standardowe API nie pozwala napisać do dowolnego salonu. Nie ma synchronizacji archiwum skrzynki ani gwarancji kompletnej historii sprzed podłączenia. Nie ma potwierdzeń dostarczenia/odczytu ani automatycznego zakładania kontaktów po podobnej nazwie.

Privacy Policy jest dostępna HTTP 200, lecz stanowi dokument testowy do uzupełnienia tożsamości administratora i zatwierdzenia przed App Review. RODO, DPA, retencja innych danych CRM i obsługa niejednoznacznych żądań osób wymagają administratora. Odtworzenie snapshotu nie zastępuje nadal niepodłączonej długoterminowej rotacji backupów offsite z wcześniejszej fazy.

WebKit oznacza emulację iPhone 13; fizycznego OAuth Meta nie testowano. Instalację PWA i logowanie na fizycznym iPhonie wcześniej potwierdził właściciel, nie Codex. Pierwszy OAuth należy wykonać w tej samej karcie Safari co logowanie CRM, aby zachować nonce; przejście PWA↔Safari może rozdzielić ciasteczka. Ekran offline WebKit testowano przez zerwanie połączenia w lokalnym proxy. TLS w testach pozostawał weryfikowany, z zaufaniem do CA proxy środowiska.

Wyszukiwanie po mieście, CRM i ręczny link Google Calendar zachowano. Promień wyszukiwania/automatyczny import zweryfikowanych leadów i Google Calendar OAuth nie zostały dodane w tym wydaniu OAuth Meta. Nie deklarujemy ukończenia całego procesu Focus 1.0 ani pełnej gotowości produkcyjnej integracji.

## URL-e i zmienne

Dokładne adresy bez końcowego ukośnika:

- Redirect URL: https://ai-focus-3-0.onrender.com/api/meta/oauth/callback
- Webhook: https://ai-focus-3-0.onrender.com/api/meta/webhook
- Deauthorize: https://ai-focus-3-0.onrender.com/api/meta/deauthorize
- Data deletion callback: https://ai-focus-3-0.onrender.com/api/meta/data-deletion
- Privacy Policy: https://ai-focus-3-0.onrender.com/api/meta/privacy

Callbacki OAuth i webhook mają na produkcji bramkę wyłączonej funkcji, więc bez konfiguracji nie obsługują prawdziwego flow. Deauthorize/data deletion wymagają podpisu i App Secret, nie logowania do CRM. W Meta data deletion należy wybrać typ callback, nie instrukcję GET.

Nazwy środowiskowe: **META_ENABLED, META_MODE, META_CONFIG_ID, META_REDIRECT_URI, META_APP_ID, META_APP_SECRET, META_VERIFY_TOKEN, META_ENCRYPTION_KEY, META_TEST_ACCOUNT_ID, PRIVACY_CONTROLLER_NAME, PRIVACY_CONTACT_EMAIL**. Wartości właściciel wpisuje wyłącznie w Render → ai-focus-3-0 → Environment; żadnych haseł ani tokenów w rozmowie. Opis każdego pola i klucza Fernet: [SETUP.md](SETUP.md).

**Konkretny następny krok w Meta:** App Dashboard → Use cases → Manage messaging & content on Instagram → Customize → API setup with Unified login → Configure your app → konfiguracja 2380634476006078 → **Redirect URL**: wpisać dokładny adres callbacka z tabeli i wybrać Save. Pozostałe warunki panelu i testów są opisane w SETUP.md; nie należy przełączać Live.

## Koszty i pliki

Dodatkowe płatne zasoby i płatne modele: **0**. Bazowy plan Render pozostaje około 13 USD/mies. plus podatki/ponadlimitowe użycie. Nie aktywowano reklam, płatnej wysyłki, modelu AI ani nowego magazynu.

Zmiany funkcjonalne: backend/meta.py, backend/meta_models.py, backend/main.py, backend/worker.py, backend/qualification.py, frontend/src/MetaPanel.tsx, frontend/src/main.tsx, migrations/env.py, migrations/versions/003_instagram_development.py, scripts/supervise.py, render.yaml. Testy: tests/test_meta.py, tests/ci_e2e.py, tests/production_browser_check.py. Dokumentacja: docs/meta/*, README.md, docs/STATUS.md i raporty.

**Focus 1.0 i Focus 2.0 nie zostały zmienione — kod, usługi, konfiguracja i dane pozostały nienaruszone.**
