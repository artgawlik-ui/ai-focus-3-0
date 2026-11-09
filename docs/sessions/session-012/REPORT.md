# RAPORT AI FOCUS 3.0.4 — SESJA 012

## DONE — zakończone kontrole i poprawki

HEAD lokalny/GitHub wejściowy c538b9a26fcd7f91232c938b894056f0a9072f25 zgodny,
PR #3 Draft, CI 42085434097 success. Zachowano trzy prywatne archiwa, bez ich otwierania/push.
Odczytano RESUME, raport i ROLLOUT 011, RELEASE_GATE, recovery 006, kod backup/offsite.

### A — dostęp SQL

Polityka Codex: TCP domains=[], ip_ranges=[], VPN=false. Poprzednia zgoda nie ustanawia
grantu. **0 prób SSH, 0 SELECT-ów**; bez obchodzenia proxy, zmian sieci i allowlisty.
Zgoda A aktualna, prywatne konta niepotwierdzone. Blokada kanału pozostaje.

### B — recovery i kod powrotu

Odczyt Render get_deploy: dep-dbjhl6jbc2fs73crj65g nadal live, commit
 d15265b26524d594bdbcb4bc6b63fcbc398a1424. Bezpieczny zapis provider-readonly.json.
Metadane nie zawierają eligibility zachowanego artefaktu ani snapshotu środowiska.
Dostępność kodu Git i start starego API potwierdzono testem; nie dowodzą one możliwości
natychmiastowego rollbacku obrazu w Render. Nie pobierano sekretów konfiguracji.

Najnowszy skuteczny punkt recovery pozostaje nieustalony; brak nowego dowodu WAL lag
lub testu PITR. Historyczne startsAt/AVAILABLE nie zastępują latest point.
Istniejący offsite jest opt-in/dzienny/retry godzinny i używa SHARE LOCK oraz bufora dumpa;
nie realizuje RPO60 przez samo włączenie. FOCUS3B1 używa AES-GCM/scrypt; odzyskanie
wymaga niezależnego, trwałego klucza/hasła i magazynu, których trwałości nie potwierdzono.
Nie odczytywano wartości sekretów, nie generowano kopii ani kluczy.

- Potwierdzone: kod rollbacku dostępny w Git, wskazany deploy live; historyczna kopia
  została odtworzona wcześniej, ale nie jest dowodem świeżości produkcji.
- Do odczytowej kontroli: latest point w Recovery/support providera; eligibility obrazu
  i env targetu; trwałość/retencja magazynu i dostęp operatora do klucza bez jego ujawniania.
- Osobna operacja/zgoda: nowy eksport, recovery/PITR, koszty, zmiany konfiguracji, rollout.
  Najpierw istniejący PITR z dowodem latest point; brak podstaw do zakupu upgrade w ciemno.

### C — próba procedury na syntetycznej bazie

4 nowe przypadki w tests/test_release_rehearsal.py:
1. Rzeczywisty worker d15265b zajmuje zadanie; obecny worker startuje paused. Stary
   otrzymuje SIGTERM podczas syntetycznego modelu i kończy zadanie. Po potwierdzeniu
   jego wyjścia nowy wznawia pracę; dokładnie 1 szkic.
2. Ten sam układ, ale stary proces zostaje zabity przed wynikiem. Zadanie pozostaje
   running. Tylko w syntetycznej bazie przesunięto wiek updated_at o 6 min zamiast
   czekać 5 min; nowy odzyskuje zadanie, zapisuje dokładnie 1 szkic. Żadnego takiego
   UPDATE nie przygotowano do wykonania na produkcji.
3. Rzeczywisty supervisor/API i worker kończący się kodem 23: supervisor zwraca 23,
   proces API jest zakończony i zebrany; nie pozostaje osierocony proces.
4. API odmawia utworzenia Job dla trwałego opt-out (409), kolejka pozostaje pusta.

W pierwszych dwóch przypadkach rzeczywiste stare API/ORM na bieżącym schemacie zwraca
health 200 i prywatne API 401; count/SHA wszystkich 17 tabel identyczne przed i po.
Stary kod pobierany jest lokalnie z Git, bez dostępu do produkcji. CI pobiera historię
(fetch-depth=0), aby ten sam test działał z prawdziwym historycznym kodem.

Model w starym procesie jest wyłącznie blokującym fixture'em HTTP; transport sieciowy
jest zablokowany. Syntetyczna flaga paid=true i syntetyczny klucz w tym subprocessie
nie aktywują zewnętrznego API — httpx.post zastąpiono fixture'em przed importem workera.
Nowy worker ma AI/Meta/offsite OFF. Podprocesy nie dziedziczą sekretów środowiska:
whitelist PATH/locale + syntetyczna konfiguracja i lokalny DATABASE_URL.

**Granice:** to nie deploy/rollback Render, test fizycznego iPhone'a ani restore.
Po cofnięciu uruchamiano stare API do odczytu, nie starą kolejkę. Stary worker nie
respektuje zabezpieczeń 010/011 ani nowego opt-out: rollback z jego uruchomieniem
wymaga potwierdzonej kontroli kolejki/retencji. Bez niej STOP, nie zakładać skuteczności
WORKER_PAUSED w d15265b. Brak nowych migracji/downgrade.

### D — funkcjonalność

CRM/role/historia/wizyty/import-export i agent regułowy mają istniejącą regresję;
nie przedstawiamy ich jako sprawdzonych teraz na produkcji. PWA: manifest, ikony,
rejestracja SW, cache wyłącznie publicznego offline.html; finalny CI ponownie sprawdza
Chromium/WebKit. Fizyczną instalację wcześniej potwierdził właściciel, nie Codex.
Google Calendar to ręczny link, nie OAuth/synchronizacja. Meta jest kodem/mockami,
bez zweryfikowanego prawdziwego konta. Livespace jest schematem adaptera.
Wyszukiwanie OSM jest po mieście, brak pełnego procesu promienia i automatycznej weryfikacji.

Naprawiono najważniejszą bezpieczną lukę w bieżącym zakresie: queue_job odrzuca także
MetaConversation.opted_out. Wspólny lock_contact + ponowny odczyt salonu po blokadzie
zapobiegają zakolejkowaniu po zatwierdzonej rezygnacji lub zmianie właściciela/statusu.
Worker zachowuje niezależną ponowną kontrolę przed szkicem.

## Testy / napotkane problemy

`DATABASE_URL=postgresql://postgres@127.0.0.1:55432/focus3_test pytest -q tests/test_release_rehearsal.py tests/test_contact_concurrency.py tests/test_api.py tests/test_agent_resilience.py tests/test_worker_lifecycle.py tests/test_supervise.py`
— **59 passed, 0 failed/skipped, 30.30 s**. Lokalny PG17, limit 256MB/1CPU, dane syntetyczne.
Pierwsza próba: 2 failed/2 passed — fixture ORM nie miało metadata alembic_version,
porównywano 16 zamiast 17 tabel. Naprawiono fixture i włączono metadata w fingerprint;
syntetyczny `alembic stamp 004` dodaje marker, nie jest dowodem wykonania migracji.
Rzeczywiste migracje pozostają osobnym testem test_meta_migration i krokiem CI.
Po poprawce pełny wyżej wymieniony zestaw 59/59. Bez ignorowania błędów.
`git diff --check` PASS; `pip check` No broken requirements found.
Ostrzeżenia AnyIO/Starlette pozostają; brak zmian zależności, modeli i migracji.
Końcowy CI dokładnego HEAD wymagany przed PASS kodu; dowód w Checks PR #3 i raporcie rozmowy.

## Zamknięte luki i otwarte bramki

Zamknięto lokalnie: brak rzeczywistej próby handoff/SIGTERM/kill, brak próby zebrania
API po błędzie startu, brak porównania danych po uruchomieniu starego API, przyjmowanie
Job mimo trwałego opt-out. Dowody powyżej; nie utożsamiać z zamknięciem bramek produkcji.
Nadal BLOCKED: aktualne 004/konta/17 tabel/retencja, RPO60, trwały magazyn/klucz,
artefakt/env rollbacku, potwierdzony handoff produkcyjnych procesów i zgoda wydania.

Najważniejsza następna czynność: ograniczony grant TCP Codex do ssh.frankfurt.render.com:22,
bez zmiany allowlisty PostgreSQL. Po nim host key/autoryzacja/prywatne ID i tylko 4 SELECT-y.
Szacunek **5 sesji podstawowych + ≥1 DM** bez zmniejszania przy otwartych wymaganiach operacyjnych.

Zmiany: backend/main.py, tests/test_release_rehearsal.py, .github/workflows/tests.yml,
RESUME.md i dokumenty 012. SHA raportu: `git log -1 --format=%H -- docs/sessions/session-012/REPORT.md`.
Bez merge/deploy/restore/nowych eksportów/produkcji/konfiguracji/płatnych zasobów/Meta/DM.
Focus 1.0/2.0 niezmienione. Prywatne archiwa nieopublikowane. PR pozostaje Draft.

## Korekta po pełnym CI

Pierwszy CI kandydata 9c15a57: workflow 42087673652, **185 passed / 1 failed**.
Błąd dotyczył istniejącego testu opt-out po unsend: zakładał przyjęcie nowego Job mimo
rezygnacji, co zmieniła nowa kontrola API. Nie wyłączono ani nie osłabiono testu.
Job jest teraz utworzony przed rezygnacją; po unsend i Meta OFF test sprawdza 409 dla
nowego Job oraz failed/brak draft dla wcześniejszego zadania uruchomionego przez worker.

Powtórzono regresję z tests/test_meta_304.py oraz wszystkimi plikami wcześniejszego
zestawu: **69 passed, 0 failed/skipped, 33.63 s** na syntetycznym PG17. Zbiór
obejmuje wcześniejsze 59 przypadków — liczb nie sumować. 4 nowe testy i 1 wzmocniony.
Końcowy commit zawiera ten test i aktualizację raportu; pełne CI nowego SHA nadal
musi zakończyć się success. Wynik końcowy w PR/raporcie rozmowy.
