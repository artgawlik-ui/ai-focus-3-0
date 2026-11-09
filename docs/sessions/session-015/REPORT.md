# RAPORT AI FOCUS 3.0.4 — SESJA 015

## Punkt wejściowy i status

Wejście 516cd335b88bca821bcd4a7e982b0a66c997de30, gałąź fix/3.0.4-meta-validation,
PR #3 Draft, wejściowe CI SUCCESS/225. Zachowano sesje 008–014 i prywatne nieśledzone ZIP-y.
Kryteria zapisano przed implementacją w ACCEPTANCE.md. Wydanie produkcyjne **BLOCKED**.
Kod/testy lokalne ukończone; końcowy PASS kodu wymaga sukcesu CI dokładnego SHA.
SHA raportu: `git log -1 --format=%H -- docs/sessions/session-015/REPORT.md`.
Dowód pełnego CI: Checks PR #3 / podsumowanie tej sesji; nie kopiować wejściowego wyniku.

## Co faktycznie zaimplementowano

OAuth z sesyjnym state, TTL5min, S256 PKCE, unikalnym hashem użytego kodu i wymianą POST
na serwerze. Odrzucanie złej sesji/użytkownika/stanu/kodu; disconnect anuluje także stan
w trakcie wymiany. Tokeny i zatwierdzone payloady Fernet, osobny klucz, minimalny scope
calendar.app.created. Nie proszono o e-mail/telefon ani inne kalendarze. Odświeżanie
serializowane; przejściowe awarie nie usuwają tokenu. Błędy statyczne, bez treści dostawcy.

Powiązanie per użytkownik, manager zatwierdza grant i nowy dedykowany kalendarz.
Tworzenie kalendarza zapisuje trwały zamiar: po niepewnym wyniku STOP/ręczna weryfikacja,
bez ponownego insert. Handlowiec nie zatwierdza cudzego grantu ani zapisów wydarzeń.
OAuth sam nie włącza zapisów. Trzy flagi domyślnie OFF, guard wewnątrz transportu.

Podgląd -> jawna zgoda managera na revision/hash -> szyfrowane zlecenie 15min -> istniejący
worker. Blokady konta/kontaktu/użytkowników/wizyty, ponowny odczyt pod blokadą, opt-out,
aktywność i przypisanie sprawdzane przed HTTP. Zmiana notatki lub adresu unieważnia
stary podgląd. Stabilne event.id, GET/insert/409, ETag i If-Match; timeout po insert
odzyskuje po ID zamiast drugiego wydarzenia. Zmiany ręczne/412 wymagają ponownej decyzji.
Retry do5 prób, backoff do300s. Cancel przez PATCH, bez DELETE/zaproszeń; audyt CRM
wyłącznie po potwierdzonym API. Historia pokazuje, gdy dawny sukces nie odpowiada CRM.

Disconnect lokalnie czyści tokeny/zlecenia, zachowuje historię/mapowania/wizyty.
Nie odwołuje zdalnego grantu Google i nie usuwa wydarzeń — komunikat UI to wyjaśnia.
Panel mobilny: połączenie, statusy, zatwierdzenie, podgląd i historia, odświeżenie podglądu.
Brak automatycznego synchronizowania wszystkich wizyt, brak aktualizacji w tle bez zgody.

## Schemat, zgodność i rollback

Cztery tabele Google w osobnym GoogleBase i opcjonalnym profilu google-alembic.ini.
Standardowy head004/17 tabel zachowany; nowy profil head005/21. Start wybiera profil
wyłącznie przy GOOGLE_SCHEMA_ENABLED=true, zgodnie z tym samym parserem flag.
Migracja testowana na osobnej syntetycznej bazie. Downgrade004 zachowuje cztery tabele;
porównanie fingerprintów20 tabel danych przed/po, marker Alembic celowo osobno.
Re-upgrade idempotentny, brak DROP/cleanup. Nie wykonano migracji produkcyjnej.
Po005 nie wolno wyłączyć schema flag przed kontrolowanym downgrade; stary profil nie zna005.
Nie zmieniono czterech zatwierdzonych SELECT-ów właściciela (tylko004/17).
Szczegółowe STOP, migracja, wyłączenie transportu i rollback w GOOGLE_CALENDAR_PLAN.md.

## Testy i dowody lokalne

`DATABASE_URL=<synthetic localhost focus3_test> .venv/bin/python -m pytest -q
 tests/test_google_calendar.py tests/test_visit_planner.py tests/test_worker_lifecycle.py
 tests/test_e2e_discovery_transport.py tests/test_meta_migration.py`

**68 passed, 0 failed, 0 skipped, 32.86s**. Wyniki wcześniejszych nakładających się
zestawów 67/67 i 1/1 nie są sumowane. Dwa ostrzeżenia deprecacji zewnętrznego test runnera
(anyio/pytest alias i TestClient httpx); nie traktowane jako podatność ani wyciszone.
Nowe przypadki pytest: **34** =32 Google +1 etap zatrzymania workera +1 fixture transportu.

Google: RBAC/CSRF/state/sesja/PKCE/replay/expiry, szyfrowanie, guardy, approval,
transient/invalid_grant, retry/429/5xx, ETag/409/412, cancel, disconnect/OAuth race,
dwa workery, edycja w trakcie synchronizacji, brak duplikacji i wycieków, profile004/005.
Syntetyczny PostgreSQL17, lokalny Docker256MB/1CPU; oddzielne bazy z prefiksem testowym.
Nie użyto kopii/danych produkcyjnych. Zmiana testu migracji i fixture uzasadniała ostatnią regresję.

`npm run build --prefix frontend` PASS (tsc+Vite6.4.5, JS258.45kB/gzip78.44kB).
`python -m compileall -q backend tests`, `sh -n scripts/start.sh`, `git diff --check` PASS.
E2E rozszerzone: oba silniki wykonują lokalny callback, zgodę managera, mock calendar,
podgląd/potwierdzony sync i cancel, weryfikują NOWY request id ze statusem synced,
rozłączenie i overflow. Żadna przeglądarka nie odwiedza Google OAuth/Calendar.
HTTP fixture fail-closed, tylko APP_ENV=test + lokalny focus3_ci_* + prywatny store plikowy;
inne HTTP blokowane. Nowy test fixture obejmuje409 i If-Match/412.
Pełne backend/build/Chromium/WebKit/npm audit/pip-audit uruchamia istniejący workflow.
Nie deklarować ich sukcesu bez zakończenia CI końcowego SHA. WebKit to emulacja,
nie test fizycznego iPhone'a; wcześniejszy test PWA właściciela nie obejmuje nowego panelu.

## Dokumentacja Google i ograniczenia

Sprawdzono publiczną dokumentację 2026-11-05, Calendar API v3; pełne linki i konfiguracja
w docs/integrations/GOOGLE_CALENDAR_PLAN.md. Potwierdzone: app.created, calendars.insert,
offline/refresh/POST token, sendUpdates, ETag/If-Match; discovery Google reklamuje S256.
Dokument Web OAuth nie opisuje PKCE wprost: test klienta Web i złego verifier na koncie
właściciela jest nadal wymagany. Nie ma fallbacku do plain/bezPKCE.
Nie wykonano rzeczywistego OAuth ani odczytu/zapisu prywatnego wydarzenia.
Mock nie jest potwierdzeniem działania z Google. Brak watch/full-resync/freebusy i zdalnego
revoke; grant usuwa użytkownik w bezpieczeństwie konta. Retencja metadanych nowych tabel
wymaga osobnej polityki/harmonogramu; payloady są czyszczone po stanach końcowych.
HTTP+commitDB nie są atomowe; stabilny ID nie oznacza exactly-once wywołania sieciowego.

## Zasoby i blokady

Bez SDK, Redis, nowej usługi/workera; istniejąca pula i proces, 1 zlecenie na przebieg.
HTTP timeout10s, możliwych kilka wywołań w transakcji; zatrzymanie może przerwać operację,
ponowienie sprawdza deterministyczny ID. Blokady podczas HTTP opóźniają równoległą edycję.
Ocena limitów Starter nie zastępuje pomiaru na rzeczywistym ruchu; brak aktywacji.
Nowe zasoby i koszty0; quota/warunki klienta na żywo niepotwierdzone.

Środowisko revision5, brak nowego kanału/grantu/settera: nie ponawiano SSH. 0 produkcyjnych
SELECT, 0 operacji Render/Meta, 0 eksportów/restore/PITR, 0 deploy/merge/realDM.
RPO60, aktualne SQL/integralność/konta, trwały magazyn/klucz, artefakt/env rollbacku
oraz handoff starych workerów pozostają BLOCKED. Nie zmieniono Focus1.0/2.0.

## Pliki i następny etap

Backend: google_calendar.py, google_models.py, google_transport.py, main.py, worker.py.
Frontend: GoogleCalendarPanel.tsx, main.tsx. Migracje: google-alembic.ini,
migrations/env.py, google_versions/005_google_calendar.py. Start: scripts/start.sh.
Testy: test_google_calendar.py, test_worker_lifecycle.py, test_e2e_discovery_transport.py,
e2e_discovery_transport.py, ci_e2e.py, production_browser_check.py.
Dokumenty: .env.example, README.md, RESUME.md, GOOGLE_CALENDAR_PLAN.md, sesja015.
Dokładny diff: `git diff --stat 516cd335..HEAD`; tylko repo Focus3, bez archiwów prywatnych.

Następny etap: potwierdzenie CI, potem osobno zatwierdzony klient Web/konto testowe OAuth;
operacyjnie ograniczony grant TCP Codex ssh.frankfurt.render.com:22, potem zaufany host,
kanał READ ONLY/prywatne ID i cztery SELECT-y. Bez zmiany allowlisty PostgreSQL.
Nie prosić ponownie o A. Wymagana osobna zgoda na produkcyjny schemat/deploy/aktywację.
**Szacunek nadal5 sesji podstawowych +≥1DM**; nowy adapter nie zamknął wymagań recovery.

## Potwierdzone pełne CI implementacji

Commit `778477c78690f59b61ece1d83f3e6cbbdf2e20a5`, workflow PR
https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42132281549,
job127611594248: **completed/success**. Log: `259 passed, 2 warnings in 84.68s`,
`chromium-desktop: PASS`, `webkit-iphone: PASS`, `found 0 vulnerabilities`,
`No known vulnerabilities found`. Build i wszystkie kroki workflow success.
225 wejściowych +34 nowe =259, bez osłabienia dotychczasowych testów.
11 operatorskich cleanup nadal poza zakresem CI; nie są testami aplikacji Google.
Kod/testy **PASS na mockach**; live OAuth/Google i produkcyjne wydanie **BLOCKED**.
Ten dopisek i RESUME to dokumentacja dowodu, bez dalszych zmian kodu.
Końcowy SHA dokumentacji również wymaga zielonego CI (Checks PR #3).
