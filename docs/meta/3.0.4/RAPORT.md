# Ai Focus 3.0.4 — issue #2: BLOCKED

**Status dotyczy kontrolowanego uruchomienia Meta: BLOCKED.** Poprawki są przygotowane do przeglądu, ale nie wdrożono ich, nie wykonano merge i nie aktywowano żadnej integracji. Działająca produkcja pozostaje **3.0.3** na https://ai-focus-3-0.onrender.com.

Zlecenie: https://github.com/artgawlik-ui/ai-focus-3-0/issues/2. Baza gałęzi `fix/3.0.4-meta-validation`: `d15265b26524d594bdbcb4bc6b63fcbc398a1424`. Nie modyfikowano Focus 1.0/2.0, produkcyjnej bazy ani ustawień Render/Meta. Wszystkie operacje Render były odczytowe. Nie wykonano żadnych rzeczywistych wywołań Instagram/Graph API, DM ani logowania właściciela hasłem.

## 1. Zweryfikowane na produkcji

- Render: live deploy **dep-dbjhl6jbc2fs73crj65g**, commit **d15265b26524d594bdbcb4bc6b63fcbc398a1424**, zakończony 2026-11-01 10:56:20 UTC; repo/main zgodne z issue. Starter `0.5c-512mb`, Frankfurt, jedna instancja, autodeploy off.
- Odczytowa walidacja `python -m tests.production_meta_readonly_check --expected-version 3.0.3`: PASS. HTTPS `/api/health` 200 + wersja 3.0.3; bez sesji auth/me, salons i meta/status = 401; GET webhook i callback OAuth = 404. Manifest standalone i service worker = 200.
- Prywatne API: `Cache-Control: no-store`, HSTS, nosniff, DENY, CSP z frame-ancestors none. Nie wykonywano testów zapisów ani podpisanych webhooków na produkcji.
- Logi: 100 ostatnich wpisów aplikacji bez dopasowań error/exception/traceback/deferred, próbka ma dalsze strony; osobne zapytanie poziomu error od 10:55 UTC zwróciło 0 i hasMore=false. Wyszukiwanie logów Running upgrade nie zwróciło potwierdzenia migracji. Brak błędu w tych filtrach nie dowodzi braku wszystkich błędów.
- Metryki 10:40–11:40 UTC (obejmują także poprzednią instancję): maks. ok. **158,5 MiB / 512 MiB**, CPU **0,00613 / 0,5**. Płatny PostgreSQL 17 `0.1c-256mb`, 1 GB, available: maks. **4 aktywne połączenia**, ok. **55,9 MiB**, CPU **0,00975 / 0,1**. To obserwacja przy wyłączonej integracji, nie benchmark realnego ruchu Meta ani dowód poprawności SQL.

Dowody: [PRODUCTION-READONLY.json](PRODUCTION-READONLY.json), [publiczny test](evidence/production-check.json), [statusy konfiguracji](evidence/config-status.json). Zapisano wyłącznie bezpieczne statusy i agregaty, nie wartości sekretów. Dodatkowy odczyt listy env groups workspace zwrócił 0, więc nie stwierdzono grup dostarczających brakujące zmienne.

## 2. Niezweryfikowane / blokady

| Warunek | Stan i przyczyna |
|---|---|
| Bieżący schemat i zawartość PostgreSQL | **BLOCKED**. Hosted MCP nie może połączyć się przy pustej allowliście zewnętrznej. Domyślny SSH trafiał na błąd właściciela systemowego pliku konfiguracyjnego; próba z pominięciem tego pliku zakończyła się connection refused. Polityka środowiska nie ma żadnych grantów TCP. Nie otwierano bazy ani nie zmieniano polityki sieci. |
| Revision 004 / dokładne liczby i SHA-256 | **Nie potwierdzono na produkcji**. Oczekiwane z kodu: 004 / 17 tabel z alembic_version. Start.sh wykonuje alembic upgrade head przed startem, a deploy jest live, lecz to nie zastępuje SELECT ani fingerprintu. Nie zakładamy 118 salonów. |
| Bieżąca zawartość inboxa i stan credential | Brak odczytu SQL: nie potwierdzono backlogu, dead-letter ani tego, czy istnieją starsze zaszyfrowane tokeny. |
| Konto właściciela / konto techniczne | Istniejąca lokalna sesja audytowa właściciela daje 401; nie ponawiano logowania i nie tworzono sesji. Aktualnego stanu kont/sesji nie potwierdzono w SQL. Wcześniejsze potwierdzenie właściciela nie jest nowym testem. |
| PITR minimum 3 dni | Potwierdzona dokumentacja i płatny typ DB; **nie potwierdzono faktycznego okna tej bazy**. GET metadanych nie zawiera danych recovery. Nie uruchomiono odtwarzania PITR. |
| Świeża szyfrowana kopia i offsite | BACKUP_PASSPHRASE puste, OFFSITE_BACKUP_ENABLED=false, wymagane pola S3/retencji puste. Historyczną kopię odtworzono, ale świeżej kopii bieżącej produkcji nie wykonano. Nie oznacza to wyłączenia zarządzanego PITR Render. |
| Meta | META_ENABLED=false; modułowe flagi nieustawione, dziedziczą false; flaga DM nieustawiona, fail-closed. META_MODE=development. Puste: META_APP_ID, META_APP_SECRET, META_VERIFY_TOKEN, META_ENCRYPTION_KEY, META_TEST_ACCOUNT_ID. CONFIG_ID i REDIRECT_URI ustawione; redirect pasuje dokładnie do adresu poniżej. Nie potwierdzono przypisania configuration ID do aplikacji, IG user ID, ról/testerów i scopes w panelu Meta. |

**Nie deklarujemy gotowości integracji z rzeczywistym kontem @artur_uluru_hair.** Nie zmieniono żadnej z powyższych wartości.

## 3. Błędy odtworzone i poprawione na gałęzi

| Problem | Ocena | Poprawka / dowód |
|---|---|---|
| Nie-ASCII w podpisie lub GET verify token powodowało HTTP 500 | niska, dostępność | Stałoczasowe porównanie bajtów UTF-8; nieprawidłowe dane dają 403. Pierwszy test regresji był czerwony. |
| Unsend usuwał body wiadomości, ale zostawiał kopię tekstu w zaszyfrowanym inboxie | średnia, prywatność | Kasowanie kopii message/echo/deleted po ID, bez kasowania minimalnych metadanych. Tombstone w odbiorze nie przechowuje tekstu/załączników. Późniejsze powtórzenie nie odtwarza treści. Pierwsze dwa testy regresji były czerwone. |
| Niespójna kolejność blokad processor/prywatność | średnia, odporność | Credential blokowane przed inboxem, ponowne sprawdzenie lease/fencing; test pokazuje, że oczekujący processor nie blokuje inboxa callbackowi prywatności. Ograniczono także SQL przy zapisie stanu niepowodzenia. |
| Usunięcie istniejącej wiadomości nie tworzyło wpisu usunięcia CRM | niska, audyt | Jeden instagram_deleted z odwołaniem do źródła, bez tekstu; duplikaty nie dodają kolejnych wpisów. |
| Błędny typ sender/recipient niepotrzebnie zużywał retry i dead-letter | niska, odporność | Walidacja struktury identyfikatora, bez tworzenia fikcyjnej konwersacji. |
| Agent ignorował utrwaloną rezygnację po unsend i wyłączeniu Meta | średnia, prywatność | Worker sprawdza MetaConversation.opted_out niezależnie od flag i zachowanej treści. Nie generuje szkicu; zadanie kończy się bezpiecznie failed, tak jak istniejący zakaz kontaktu. Osobny test czerwony przed poprawką. |

Nie ma nowej migracji, zmiany schematu, rotacji kluczy ani zmiany semantyki flag. Wersja kodu kandydata: 3.0.4. Format Fernet zachowany. Transport DM pozostał niezaimplementowany: brak/pusta/błędna flaga = 403 wewnątrz transportu; nawet true = 501 bez żądania HTTP.

## 4. Testy — wykonane, nie symulowane wyniki

| Kontrola | Polecenie / wynik |
|---|---|
| Baseline d15265b | `.venv/bin/python -m pytest -q --tb=no --show-capture=no`: **80 passed**, 0 failed/errors/skipped |
| Odtworzenie błędów | `pytest tests/test_meta_304.py`: pierwsze 3 przypadki **3 failed**; osobny test rezygnacji **1 failed** przed poprawką |
| Pełny zestaw po poprawkach | `PYTHONPATH=/tmp/focus3-readonly-audit:. .venv/bin/python -m pytest -p network_guard -q --tb=no --show-capture=no`: **90 passed**, 0 failed/errors/skipped |
| Frontend | `npm run build --prefix frontend`: TypeScript + Vite PASS |
| E2E | `python -m tests.ci_e2e`: Chromium desktop PASS, WebKit iPhone 13 PASS |
| Zależności | `npm audit --prefix frontend --json`: **0**; `pip-audit -r requirements.txt --format=json`: **0 znanych podatności** |
| Zasoby lokalne | `python -m tests.meta_resource_probe`: 20/20 webhooków przetworzonych, maks. ack 27,42 ms, peak RSS 346,07 MiB supervisor+API+istniejący agent; bez limitu CPU Render i bez procesu backupu |
| Produkcja, wyłącznie GET | `python -m tests.production_meta_readonly_check --expected-version 3.0.3`: PASS |
| Format zmian | `git diff --check`: PASS |

Testy funkcjonalne i współbieżności używały syntetycznych danych oraz lokalnych PostgreSQL. Wymuszenie transportu httpx blokowało rzeczywiste Graph/Instagram; guard zarejestrował 0 zewnętrznych prób HTTP w pytest. E2E: logowanie/wylogowanie, CRM read/write na osobnej lokalnej bazie, szkice, brak przewijania poziomego, manifest/ikony, bezpieczny offline i brak CRM w cache. **WebKit to emulacja, nie fizyczny iPhone**; offline sprawdzony przez lokalny proxy przerywający połączenie. Pozostają ostrzeżenia deprecacji AnyIO/pytest i Starlette TestClient/httpx, nie błędy testów.

Pełny zestaw obejmuje wcześniejsze testy szyfrowania i kompatybilności, owner/CSRF/state/nonce, replay kodu, exact redirect, HMAC surowego body, commit przed ack, deduplikację równoległych webhooków, SKIP LOCKED, lease/restart, backoff/dead-letter, rollback CRM po awarii, /refresh timeout/5xx, single-flight, potwierdzone is_valid=false i ochronę nowego tokenu przed starym wynikiem. Dołożono 10 przypadków 3.0.4.

## 5. Recovery / PITR / dane

Dokumentacja https://render.com/docs/postgresql-backups (odczyt 2026-11-01, HTTP 200): płatne bazy mają ciągłe kopie PITR; workspace Hobby: 3 dni, Pro+: 7 dni. Nie można odtwarzać ostatnich 10 minut. Operacja tworzy nową instancję i wymaga osobnej zgody kosztowej. Eksporty logiczne Render przechowuje 7 dni. To fakty produktu, nie potwierdzenie aktualnego okna naszej bazy.

Istniejący historyczny zaszyfrowany artefakt odtworzono wyłącznie do nowej lokalnej bazy: manifestowe liczby i SHA-256 zgadzają się; 10 tabel z metadanymi przed migracją, 17 po migracjach, wszystkie 9 dawnych tabel danych bez zmian. Nie uruchamiano na tych historycznych danych testów funkcjonalnych ani nie wysyłano ich do modeli. Lokalną kopię usunięto po kontroli. **Nie jest to świeży backup, test PITR ani dowód integralności aktualnej produkcji.** Dowód: [historical-restore.json](evidence/historical-restore.json).

Retencja zakończonego inboxa 7/90 dni oraz wiadomości 30/90 dni zachowana. Pending/failed/dead-letter nie są automatycznie kasowane: wymagają ustalonego SLA przeglądu i decyzji retencyjnej właściciela. Usunięcie w aplikacji nie czyści retroaktywnie starszych kopii; polityka backupów i respektowanie usunięć po odtworzeniu wymagają procedury administratora. Podstawa prawna, tożsamość administratora, minimalizacja, rezygnacja i transfery/DPA pozostają warunkami przed rzeczywistym uruchomieniem; raport nie jest opinią prawną ani potwierdzeniem pełnej zgodności RODO.

Pula: 2 połączenia/proces, overflow 0, timeout 5 s; API+agent do 4. Inbox: 64 KiB, 50 zdarzeń/request, batch 4, cykl 2 s, lease 120 s, 5 prób; monitoring co 60 s. Brak nowej instancji/wątku przetwarzania/Redis. Przy PG 0.1 CPU/256 MB trzeba zmierzyć docelowy ruch i równoległy backup; istniejący backup buforuje dump w pamięci. Nie zwiększano planu ani kosztów.

## 6. Meta — kod i dokumentacja v26.0

Ścieżka to **Instagram API with Unified Login / Facebook Login for Business**, z **Meta App ID/Secret i config_id**, nie Instagram Login/Instagram App ID. Wymagane minimalne scope: instagram_basic i instagram_manage_messages; public_profile dopuszczone implicit. Nadmiarowe scope z domyślnej konfiguracji Meta są odrzucane. Właściciel potwierdza zatwierdzony IG user ID; sama nazwa profilu nie uprawnia konta.

Zweryfikowano oficjalne źródła 2026-11-01, HTTP 200 i SHA-256 w [DOCUMENTATION-EVIDENCE.json](DOCUMENTATION-EVIDENCE.json):

- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/get-started — wymiana kodu GET /v26.0/oauth/access_token, poświadczenia Meta, SUAT i przypisane konta.
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/authentication — ścieżka Unified Login, nie ig_refresh_token. Istniejący /refresh sprawdza SUAT, nie obiecuje wydłużenia go bez ponownego OAuth.
- https://developers.facebook.com/docs/graph-api/reference/debug_token/ — GET /v26.0/debug_token z input_token i wynik is_valid.

Nie potwierdzono obsługi POST body w miejsce GET tych operacji; protokołu nie zmieniono. Ryzyko wymaganych parametrów URL pozostaje: wyciszone logi wire httpx/httpcore i stałe kategorie błędów, brak sekretów w API/logach/testowych raportach. Przed dodaniem APM/proxy trzeba zagwarantować redakcję query i nagłówków. Kod nie może zagwarantować polityki przyszłego monitoringu.

OAuth zachowuje sesję właściciela, nonce, state 10 minut, jednokrotność kodu oraz identyczne redirect_uri w autoryzacji i wymianie. Podpis GET/POST i signed_request prywatności zachowane. /refresh nie usuwa tokenu przy timeout/5xx; automatyczne unieważnienie wymaga jawnego debug_token is_valid=false. Disconnect/deauthorize to odrębne jawne odwołanie. Żadnego z tych przepływów nie sprawdzano na rzeczywistym Instagramie w tym zadaniu.

Redirect: **https://ai-focus-3-0.onrender.com/api/meta/oauth/callback** (bez końcowego ukośnika). Wszystkie pola paneli, adres webhooka i callbacków, wymagania Development/testerów/App Review: [CHECKLIST.md](CHECKLIST.md). API nie jest podstawą do cold DM do dowolnego salonu; ręczny kontakt i każda przyszła wysyłka wymagają osobnej decyzji. Webhook nigdy automatycznie nie odpowiada.

## 7. Decyzja i dostarczenie

**BLOCKED** dla aktywacji produkcyjnej. Warunki: zatwierdzony odczyt SQL i integralność, wyłączone konto techniczne, aktualne recovery/PITR i świeża zweryfikowana kopia, komplet prawidłowej konfiguracji Meta, role i minimalne scope, retencja/RODO oraz osobna zgoda na merge/deploy/autoryzację/odbiór. Transport DM pozostaje poza zakresem i zablokowany.

[Checklist uruchomienia](CHECKLIST.md), [rollback](ROLLBACK.md), [plan odczytu SQL](READONLY-SQL.sql). Właściciel nie przekazuje sekretów w rozmowie. Najbliższa czynność panelowa bez zmiany zasobów: **Render → ai-focus-3-0-db → Recovery → sprawdzenie dostępnego okna PITR**; bez Start Recovery. Następnie potrzebny zatwierdzony kanał odczytu SQL, bez otwierania bazy publicznie. Nie wymagamy ręcznych poleceń technicznych od właściciela.

Zmiany kodu: backend/main.py, backend/meta.py, backend/meta_inbox.py, backend/worker.py. Testy: tests/test_meta_304.py, tests/production_meta_readonly_check.py. Dokumenty/dowody: docs/meta/3.0.4/. `git diff origin/main --stat` obejmuje wyłącznie repo Focus 3.0; niezwiązane archiwa reports/*.zip pozostawiono nietknięte. Bez zmian w migrations/, render.yaml, Dockerfile, zależnościach, konfiguracji produkcyjnej i innych projektach.

## 8. Artefakty i źródła dowodów

[RESULTS.json](RESULTS.json), [baseline](evidence/baseline-junit.xml), [końcowy JUnit](evidence/backend-junit.xml), [regresje przed poprawką](evidence/regressions-before-fix.log), [rezygnacja przed poprawką](evidence/optout-before-fix.log), [przeglądarki](evidence/browser-check.json), [build](evidence/build.log), [audyt npm](evidence/npm-audit.json), [audyt pip](evidence/pip-audit.json), [guard](evidence/network-guard.json), [zasoby](evidence/resources.json).

Dokumentacja Render odczytana 2026-11-01: https://render.com/docs/deploys.md, https://render.com/docs/health-checks.md, https://render.com/docs/rollbacks.md, https://render.com/docs/postgresql-backups.md. Odczyt nie uruchamiał operacji opisanych w tych dokumentach.
