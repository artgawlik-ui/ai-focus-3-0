# Ai Focus 3.0 — audyt i bramka wdrożenia, 2026-10-28

**Stan: CRM działa przez HTTPS; aktualizacja bezpieczeństwa NIE jest dopuszczona do produkcji. Nie deklarujemy pełnej gotowości produkcyjnej.**

Adres: https://ai-focus-3-0.onrender.com

Produkcja: commit `e0e6b50339f5abf94b62e79a92fb3450e4e7170d`, Render `srv-dbh1rk6tlv9c73dloq20`, wdrożenie `dep-dbh341ghpmmc738m6tn0` ze statusem `live`. Bazą pozostaje wyłącznie `ai-focus-3-0-db`, ID `dpg-dbh1b0gm7kps73f0p2m0-a`, PostgreSQL 17, Frankfurt, plan 0.1c-256mb, 1 GB, zewnętrzna allowlista pusta. Koszt bazowy około 13 USD/miesiąc. Nie tworzono dodatkowych płatnych zasobów.

## 1. Audyt zależności

| Wariant | Wynik | Decyzja |
|---|---|---|
| Frontend kandydacki, Vite 6.4.5 | `npm audit --prefix frontend`: 0 podatności | Zmiana w tej samej wersji głównej, kompilacja i E2E pozytywne |
| Backend zgodny z ograniczeniem wersji głównych: FastAPI 0.162.0, Starlette 0.52.1, multipart 0.0.32, cryptography 46.0.7 | `pip-audit -r requirements.txt`: 17 wpisów, 9 unikalnych GHSA | Bramka bezpieczeństwa pozostaje czerwona; nie wdrażamy |
| Backend testowany lokalnie ze Starlette 1.3.1 i cryptography 50.0.2 | `pip-audit`: 0 znanych podatności; 14 testów i Chromium/WebKit pozytywne | NIE wdrażamy: zmienia główne wersje bibliotek, czego właściciel zabronił |

17 wpisów audytora obejmuje powtarzające się aliasy PYSEC/GHSA. Dziewięć unikalnych poradników według oficjalnego GitHub Advisory API: **5 high, 3 medium, 1 low**, bez critical w tym zestawie. Szczegóły i odnośniki: `docs/audit/advisory-severities.json`, `docs/audit/pip-audit-compatible.json`. Frontend: `docs/audit/npm-audit.json`.

| Pakiet / poradnik | Waga | Pierwsza poprawka wskazana przez audyt |
|---|---|---|
| Starlette, GHSA-82w8-qh3p-5jfq — limity formularza urlencoded | high, CVSS 7.5 | 1.3.1 |
| Starlette, GHSA-86qp-5c8j-p5mr — interpretacja Host | medium, 6.5 | 1.0.1 |
| Starlette, GHSA-jp82-jpqv-5vv3 — interpretacja ścieżki | low, 3.7 | 1.3.0 |
| Starlette, GHSA-wqp7-x3pw-xc5r — UNC na Windows | high, 7.5 | 1.1.0 |
| Starlette, GHSA-x746-7m8f-x49c — HTTPEndpoint | medium, 5.3 | 1.1.0 |
| cryptography, GHSA-537c-gmf6-5ccf — OpenSSL w wheel | high, 7.5 | 48.0.1 |
| cryptography, GHSA-g6cj-pr64-35w5 — PKCS7 | high | 50.0.0 |
| cryptography, GHSA-jwv3-5hgf-82ww — łańcuchy certyfikatów | high | 49.0.0 |
| cryptography, GHSA-m2h6-j472-rp4c — ograniczenia nazw certyfikatów | medium | 49.0.0 |

Aplikacja działa na Linux i nie używa klas HTTPEndpoint ani operacji PKCS7/X509 z cryptography; szyfrowanie kopii używa AES-GCM i scrypt. Ogranicza to część powierzchni ataku, **nie usuwa podatności pakietów** i nie jest podstawą do oznaczenia audytu jako zielonego. Kandydat ma dodatkowe limity ciała żądań przed parserem JSON/multipart, również dla chunked transfer.

## 2. Dowody testów

- `DATABASE_URL=<izolowana focus3_test> python -m pytest -q --junitxml=test-results/backend-compatible.xml`: **14 passed**. Zakres: login/logout, hasła, cookies/sesje, CSRF, Origin, role i właściciele, dezaktywacja kont, CRM CRUD, duplikaty, optimistic locking, historia, import atomowy, eksport/formuły, wizyty/kolizje, trasy, KPI, kolejka agenta bez wysyłki, szkolenia, limity żądań.
- `npm ci --prefix frontend` i `npm run build --prefix frontend`: **PASS**, TypeScript + Vite 6.4.5.
- `python -m tests.isolated_release_check`: **PASS**. Odtworzenie zaszyfrowanej kopii do nowej lokalnej bazy; E2E Chromium desktop i WebKit z profilem iPhone 13; zapis tylko na kopii.
- `python -m tests.ci_e2e`: **PASS** lokalnie na całkowicie syntetycznej nowej bazie. CI jest rozszerzone o ten sam scenariusz i audyty; wynik audytu blokuje zielony status wydania.
- PWA/E2E: login, sesja po odświeżeniu, formularz edycji, wyszukiwanie/profil, manifest, obie ikony, apple-mobile-web-app-capable, aktywny service worker, brak poziomego przewijania i ekran offline; brak błędów JavaScript.
- WebKit offline: sprawdzony przez kontrolowane zerwanie połączenia w lokalnym proxy. Przełącznik offline protokołu testowego WebKit zwracał błąd wewnętrzny; nie traktujemy go jako dowodu fizycznego trybu samolotowego iPhone'a.
- Nie wykonano testu na fizycznym iPhonie ani rzeczywistego dotknięcia „Do ekranu początkowego”.

## 3. Integralność i konta

Przed i po ponownym wdrożeniu e0e6b50 porównano liczby i SHA-256 wszystkich **10 tabel**, z jedną i tą samą sesją odczytową: **zgodne**. Dowód lokalny: `test-results/production-redeploy-integrity.json`, polecenie `python tests/production_integrity_check.py compare`.

Punkt odniesienia: activities 6, alembic_version 1, appointments 1, integration_links 0, jobs 1, login_attempts 0, salons 1, sessions 2, trainings 0, users 2. Jedyny salon to wyraźnie oznaczony, nieaktywny `[TEST TECHNICZNY]`, nie rzeczywisty klient. Wizyta testowa jest anulowana, zadanie agenta zakończone ze `sent=false`. Nie importowano deklarowanych 118 salonów, których źródła nie zweryfikowano.

**Po tym porównaniu** zgodnie z poleceniem wyłączono konto verification@focus.invalid i skasowano jego sesje; ponowny GET `/api/auth/me` tą samą sesją zwrócił 401. To celowo zmieniło tabele users/sessions. Nie przedstawiamy starych skrótów tych tabel jako skrótów stanu po porządkowaniu. `VERIFICATION_PASSWORD` wyłączono w środowisku; konto nie będzie ponownie aktywowane.

Konto art.gawlik@gmail.com było aktywnym menedżerem przed porządkowaniem i nie było zmieniane. Sprawdzono logowanie roli menedżera kontem technicznym, **nie poznawano ani nie zmieniano hasła właściciela**. Bez bezpiecznej autoryzacji do sekretów nie można niezależnie potwierdzić końcowego logowania dokładnie tym hasłem ani wykonać nowego odczytowego snapshotu po porządkowaniu.

## 4. Kopie i wdrożenie

Pobrano zaszyfrowany AES-GCM/pg_dump snapshot nowej bazy produkcyjnej i odtworzono go w nowej, lokalnej bazie PostgreSQL 17. Liczby i SHA-256 wszystkich tabel aplikacji zgodne; lokalny cel po teście usunięto. Odmowa odtwarzania do niepustej bazy również sprawdzona. Dowód: `test-results/production-restore-check.json`, `python -m tests.production_restore_check`.

Ten snapshot pochodzi sprzed wyłączenia konta technicznego. **Nie nazywamy go świeżą kopią do kolejnego wdrożenia.** Nowe wdrożenie jest wstrzymane do zielonego audytu zgodnego z polityką wersji oraz wykonania świeżej kopii. Punkt powrotu zapisano: e0e6b50 / dep-dbh341ghpmmc738m6tn0. Nie wykonywano rollbacku; nie deklarujemy przećwiczonego wycofania.

Render dokumentuje ciągłe PITR dla płatnego PostgreSQL: 3 dni dla Hobby, 7 dla Pro+. Nie uruchamiano natywnego PITR, bo tworzy kolejną płatną instancję. To inny mechanizm niż przetestowana szyfrowana kopia logiczna. Długoterminowa rotacja szyfrowanych plików w niezależnym magazynie, alerty i automatyczne testy odtwarzania nie są jeszcze skonfigurowane. Procedura: `docs/RECOVERY.md`.

## 5. Bezpieczeństwo konfiguracji

- API bez publicznego CORS; mutacje weryfikują Origin i CSRF. Cookies HttpOnly, Secure na produkcji, SameSite=Strict. Hasła Argon2, limit prób logowania, role/ownership i blokada ostatniego menedżera.
- PostgreSQL ma pustą allowlistę dostępu zewnętrznego; aplikacja korzysta z sieci prywatnej. Starej bazy Focus 2.0 nie otwierano.
- HSTS, CSP, X-Frame-Options, no-store dla API, brak przechowywania prywatnego CRM w cache PWA. Cache zawiera wyłącznie publiczny offline.html.
- Wzorcowy skan 70 historycznych blobów Git: 0 dopasowań tokenów GitHub/OpenAI i produkcyjnych URL PostgreSQL. Prywatny katalog sekretów nie jest śledzony. To ograniczony skan wzorców, nie formalny dowód braku każdego możliwego sekretu.
- Logi aplikacji zapisują request ID, metodę i status, bez body/sekretów. Odczyt logów błędów Render w audycie zwrócił pustą listę.
- RODO: istnieje zakaz kontaktu i kontrola dostępu; polityka prawnych podstaw kontaktu, zgód, okresów retencji danych klienta i obsługi żądań osób wymaga dalszego wdrożenia i ustaleń administratora danych.

## 6. Co działa i co nie jest podłączone

Działa: CRM, role, historia, Excel, terminy i kolizje, kalendarz lokalny, link Google Calendar/Maps, KPI i lejek, szkolenia, agent regułowy/szkice, manifest/PWA, szyfrowany eksport bazy. Wyniki finansowe są potencjałem i prognozą opartą na jawnych wagach, nie księgą zamówień.

Nie jest aktywne: model AI, Meta/Instagram OAuth i wiadomości/webhooki, monitoring odpowiedzi, Google Calendar OAuth i synchronizacja, Livespace, optymalizacja tras według ruchu, push/e-mail, długoterminowe automatyczne pliki backupu offsite. Nie wysłano wiadomości klientom. Każda wysyłka pozostaje wyłączona.

Instalacja: otwórz HTTPS w Safari → Udostępnij → Do ekranu początkowego. Do CRM potrzebny jest internet; offline działa bezpieczny ekran informacyjny.

## 7. Blokady i niezależność

1. Poprawki eliminujące pozostałe podatności wymagają nowych głównych wersji Starlette/cryptography. Obecne polecenie zabrania ich wdrożenia. Nie obchodzimy tej polityki.
2. Do świeżej kopii i końcowego odczytu jako właściciel potrzebny jest działający oficjalny dostęp Render. CLI kończyło sesje błędem slow_down; oficjalny kod nie obsługuje tego błędu backoffem. Nowa sesja jest wstrzymana przed odpytywaniem do zatwierdzenia przez właściciela.
3. Nie wykonywano instalacji na fizycznym iPhonie.

Focus 1.0 i Focus 2.0: **bez zmian w repozytoriach, usługach, konfiguracji sieciowej i danych**. Zmiany wykonywano wyłącznie w nowym repozytorium/projekcie, nowej bazie Focus 3.0 i lokalnych kopiach testowych.

## Zmienione pliki kandydata

- `requirements.txt`, `frontend/package.json`, `frontend/package-lock.json`: warianty aktualizacji zależności; brak wdrożenia wersji głównych.
- `backend/limits.py`, `backend/main.py`: limity żądań przed parserem i serializacja ochrony ostatniego menedżera.
- `scripts/backup.py`: odczyt spójnego snapshotu i poprawne rozpoznawanie tabel również przy odtwarzaniu starszego schematu.
- `tests/test_api.py`, `tests/production_browser_check.py`, `tests/ci_e2e.py`: regresja bezpieczeństwa, jawny test wylogowania/cache i syntetyczne E2E dla CI.
- `.github/workflows/tests.yml`: uruchamianie regresji, Chromium/WebKit i audytów; czerwony audyt blokuje zielony wynik wydania.
- `README.md`, `docs/STATUS.md`, `docs/RECOVERY.md`, `docs/AUDIT.md`, `docs/audit/*`: status, ryzyka, procedury i dowody.

Obecna gałąź z nowymi głównymi wersjami jest wyłącznie przetestowaną propozycją do przeglądu; nie została scalona do main ani wdrożona.
