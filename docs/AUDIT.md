> Raport historyczny wydania 0c44401. Aktualne wdrożenie i wyniki faz 1–2: [phase2/REPORT.md](phase2/REPORT.md).

# Ai Focus 3.0 — raport wdrożenia, 2026-10-28

CRM działa: https://ai-focus-3-0.onrender.com. Zweryfikowano zakres CRM; pełna platforma autonomicznej sprzedaży i wszystkie wymagania operacyjne nie są jeszcze ukończone.

## Wdrożenie i autoryzacja

Render: `srv-dbh1rk6tlv9c73dloq20`, deploy `dep-dbh4jsd9el5s73ap7n50`, **live**, zakończony 19:16:58 UTC. Faktycznie uruchomiony commit: `0c44401d2b8ef2b7d11813e35aed69ab3b0de6fe`. Późniejsze zmiany raportów nie zmieniają wersji uruchomionej aplikacji. Właściciel wyraźnie zatwierdził odstępstwo dla głównych wersji Starlette i cryptography („Zezwalam”).

Przed wdrożeniem: zielone testy i powtórzony audyt, świeża zaszyfrowana kopia i udane odtworzenie. Punkt powrotu: `e0e6b50339f5abf94b62e79a92fb3450e4e7170d`, deploy `dep-dbh341ghpmmc738m6tn0`. Rollback nie był potrzebny ani przećwiczony. Nie zmieniano schematu produkcji. Blueprint validation: valid=true, totalActions=0. Auto-deploy wyłączony.

Ta sama baza: `ai-focus-3-0-db`, `dpg-dbh1b0gm7kps73f0p2m0-a`, PostgreSQL 17, Frankfurt, 1 GB, pusta zewnętrzna allowlista. Koszt bazowy około 13 USD/mies. plus podatki/ponadlimitowe zużycie; brak nowych płatnych zasobów.

## Testy i bezpieczeństwo — dowody

Pełne CI uruchomionego commita: [main SUCCESS](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/40752621425), [kandydat SUCCESS](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/40750756186).

| Kontrola | Polecenie / dowód | Wynik |
|---|---|---|
| Backend/API na izolowanym PostgreSQL | `python -m pytest -q`, backend-major-candidate.xml | 14 passed |
| Frontend | `npm ci --prefix frontend`; `npm run build --prefix frontend` | PASS, TypeScript + Vite |
| E2E Chromium i WebKit/iPhone 13 | `python -m tests.ci_e2e`; `python -m tests.isolated_release_check` | oba silniki PASS, zapisy tylko na kopii |
| Restart API i osobnego workera | `python -m tests.system_check` | CRM, historia i zadanie przetrwały restart |
| Python dependencies | `pip-audit -r requirements.txt` | 0 znanych podatności |
| Frontend dependencies | `npm audit --prefix frontend` | 0 podatności |
| HTTPS, gotowość, konta, integralność | final-production-readonly-audit.json | PASS, GET health 200, anonimowy CRM 401 |
| Świeża kopia i odtworzenie | fresh-backup-restore.json | zgodne liczby i SHA-256 wszystkich 10 tabel |

Wdrożone: FastAPI 0.162.0, Starlette 1.3.1, cryptography 50.0.2, python-multipart 0.0.32, Vite 6.4.5. Log instalacji Render potwierdza wersje backendu. Wariant bez zmiany wersji głównych miał 9 unikalnych GHSA: 5 high, 3 medium, 1 low; nie został wdrożony. Historyczne wyniki i identyfikatory są w `docs/audit/pip-audit-compatible.json` i `advisory-severities.json`; aktualny zerowy wynik w `pip-audit-major-candidate.json`. Zero znanych podatności nie jest gwarancją braku przyszłych podatności.

Testy obejmują login/logout i sesje, zmianę hasła, Origin/CSRF, role i ownership, ostatniego menedżera, deaktywację, CRM tworzenie/edycję/historię/duplikaty/optimistic locking, Excel i ochronę formuł, wizyty/kolizje, agent bez wysyłki, KPI, szkolenia, backup i limity żądań również chunked. Brak wildcard CORS. Hasła Argon2; cookies Secure/HttpOnly/SameSite=Strict; HSTS/CSP; API no-store. Limity ciała żądania działają przed parserami.

Skan historycznych blobów Git wykrył 0 dopasowań sprawdzanych wzorców tokenów i produkcyjnych URL PostgreSQL (`docs/audit/secret-scan.json`). To ograniczony skan wzorców. Sekrety i kopie nie są śledzone przez Git. Przegląd logów błędów Render po wdrożeniu zwrócił pustą listę.

Końcowy test produkcyjnego UI: Chromium desktop i WebKit/iPhone 13 — PASS; 0 żądań modyfikujących, 0 błędów JavaScript, wyłącznie publiczny offline.html w cache. Dowód: `final-production-ui.json`. Po tych testach ponownie potwierdzono wszystkie 10 skrótów.

## Dane po wdrożeniu

Odczyt z tą samą sesją właściciela: **liczby i SHA-256 wszystkich 10 tabel identyczne ze świeżym punktem odniesienia sprzed wdrożenia**. Dowód: `final-production-readonly-audit.json`. Konto właściciela zalogowane poprawnie i sesja przetrwała wdrożenie. Konto `verification@focus.invalid` nieaktywne, jego sesje unieważnione; poprzednia sesja zwracała 401. Sekret aktywacji technicznej wyłączony.

| Tabela | Rekordy |
|---|---:|
| activities | 6 |
| alembic_version | 1 |
| appointments | 1 |
| integration_links | 0 |
| jobs | 1 |
| login_attempts | 0 |
| salons | 1 |
| sessions | 1 |
| trainings | 0 |
| users | 2 |

Jedyny salon jest nieaktywnym, jawnie oznaczonym rekordem technicznym; wizyta anulowana, zakończony szkic ma sent=false. **Nie zmigrowano 118 salonów** — źródło tej liczby pozostaje niezweryfikowane. Nie odtwarzano kopii na produkcji i nie modyfikowano klientów w końcowych testach.

## PWA i iPhone

Chromium i WebKit z profilem iPhone 13: login/logout, utrzymanie sesji, CRM, formularz edycji na kopii, brak poziomego przewijania, manifest, ikony, metadane Apple, service worker, ekran offline i cache zawierający wyłącznie publiczny offline.html — PASS. WebKit offline sprawdzono przez zerwanie połączenia w lokalnym proxy; natywny przełącznik testowy zwracał błąd silnika. Nie wykonano testu na fizycznym iPhonie ani rzeczywistej instalacji z Safari.

Instalacja: otwórz adres HTTPS w Safari → Udostępnij → Do ekranu początkowego. CRM wymaga internetu; offline dostępny jest bezpieczny ekran informacyjny, bez prywatnych danych.

## Kopie i ryzyka operacyjne

Świeża kopia pg_dump zaszyfrowana AES-256-GCM/scrypt została pobrana przed wdrożeniem, odtworzona do nowej lokalnej bazy i porównana dla wszystkich 10 tabel. Odmowa odtwarzania do niepustego celu także przetestowana. Procedura: [RECOVERY.md](RECOVERY.md).

Render dokumentuje ciągłe PITR płatnego PostgreSQL (3 dni Hobby / 7 Pro+); natywnego PITR nie uruchamiano, ponieważ wymaga dodatkowej instancji. **Długoterminowy automatyczny harmonogram szyfrowanych plików offsite, retencja i alerty nie są skonfigurowane.** To otwarta luka operacyjna, nie ukończona funkcja. Brak MFA/resetu e-mail; RODO wymaga dalszych zasad zgód, podstaw kontaktu, retencji i obsługi praw osób.

## Zakres działający i dalsza implementacja

Działa: CRM, role, historia, Excel import/podgląd/eksport, wizyty i kolizje, lokalny kalendarz, ręczne linki Google Calendar/Maps, KPI/lejek/prognozy potencjału, szkolenia, trwała kolejka agenta i regułowe szkice, PWA oraz szyfrowana kopia logiczna. Nie ma księgi rzeczywistego przychodu.

Niepodłączone lub nieukończone: płatny model AI, Meta/Instagram OAuth/API/webhooki i analiza odpowiedzi, Google Calendar OAuth/synchronizacja, Livespace adapter, optymalizacja tras według ruchu, push/e-mail, automatyczne offsite backupy. Kod odkrywania salonów przez publiczny OSM/Overpass istnieje, ale dostępności zewnętrznego dostawcy nie potwierdzono w końcowym audycie. Agent niczego nie wysyła i nie umawia autonomicznie wizyt. Nie wysłano wiadomości klientom.

## Zmienione pliki wydania względem poprzedniej produkcji

`requirements.txt`, `frontend/package.json`, `frontend/package-lock.json`, `backend/limits.py`, `backend/main.py`, `scripts/backup.py`, `tests/test_api.py`, `tests/production_browser_check.py`, `tests/ci_e2e.py`, `.github/workflows/tests.yml`, `README.md`, `docs/AUDIT.md`, `docs/STATUS.md`, `docs/RECOVERY.md`, `docs/audit/account-cleanup.json`, `docs/audit/advisory-severities.json`, `docs/audit/npm-audit.json`, `docs/audit/pip-audit-compatible.json`, `docs/audit/pip-audit-major-candidate.json`, `docs/audit/secret-scan.json`. Końcowy raport dodaje wyłącznie dokumentację i odfiltrowane dowody.

Focus 1.0 i Focus 2.0: **nie zmieniano ich repozytoriów, usług, konfiguracji ani danych**. Wszystkie zmiany ograniczono do Focus 3.0 i odizolowanych lokalnych kopii. Nie są wymagane dodatkowe autoryzacje do zakończonego wdrożenia CRM; przyszłe integracje wymagają osobnej konfiguracji w oficjalnych panelach.
