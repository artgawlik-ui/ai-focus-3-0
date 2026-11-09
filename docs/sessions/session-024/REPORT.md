# RAPORT AI FOCUS3.0.4 — SESJA024

## Cel i stan wejścia

Przygotowanie wydania, nie uruchomienie produkcji. HEAD80f4652f0b3fd47301c49ccb3a27baddc630ebc3,
PR3Draft i oba pełne workflow42647145719/42647135285 SUCCESS/359 PASS potwierdzone.
RESUME i raport023 odczytane. Prywatnych ZIP-ów nie otwarto ani nie dodano do Git.
Kryteria zapisano przed implementacją w ACCEPTANCE.md.

## Faktycznie wykonane kontrole

- Środowisko revision5 current/enforced, TCP domains/ip_ranges puste, VPNfalse, brak
  zatwierdzonego Shell. **0 SSH,0 SQL produkcji**. Konektora publicznego SQL nie użyto
  jako obejścia; osobne połączenie per zapytanie nie realizuje zatwierdzonego snapshotu.
- Pakiet czterech SELECT-ów005 niezmieniony, render_sql zgodny, SHA w SQL_EXECUTION_PLAN.
  Prywatnych tożsamości kont nie odgadywano. A nadal004/17, nie native006/007.
- RenderGET w istniejącym, wcześniej wskazanym My Workspace: PostgreSQL17 available,
  0.1c-256mb/1GB/Frankfurt/bezHA, publiczna allowlista pusta. Usługa0.5c-512mb Docker,
  jedna instancja, main, autoDeploy=no. Lista deployów i get_deploy potwierdzają live
  d15265b26524d594bdbcb4bc6b63fcbc398a1424 / dep-dbjhl6jbc2fs73crj65g.
- Metadane nie zawierają latest recovery/WAL lag, PITR eligibility, artefaktu rollbacku
  ani snapshotu env. Nie pobierano wartości env/sekretów. Wynik zanonimizowany:
  provider-readonly.json. Nie twierdzimy, że historyczny AVAILABLE PITR jest aktualny.
- Oficjalne dokumenty Render Recovery/Backups, Rollbacks i Private Network: HTTP200,
  odpowiednie sekcje odczytane2026-11-09. PITR płatnych baz jest funkcją, nie dowodem RPO.
  Historyczny snapshot005 zachowuje dowód odtworzenia17/23/004, nie świeżości produkcji.
  Retencja logical backups w Render7dni: starej kopii nie można uznać za nadal dostępną.

## Konkretna naprawa i nowe dowody

Dockerfile nie kopiował native-alembic.ini, choć start.sh go wymaga dla native profilu.
Dodano wyłącznie COPY istniejącego pliku. Test buduje rzeczywiste instrukcje COPY
w lokalnym obrazie scratch bez sieci/RUN, odczytuje wynikowy filesystem i wykonuje
Alembic discovery w tym artefakcie. Baseline80f rzeczywiście nie ma native ini;
po poprawce dostępne standardowe004 i opcjonalne007. To test pakowania COPY, nie pełny
build obrazu Python/npm/OS ani test artefaktu Render. Nie rozwijano Google.

Trzy nowe próby procesu/DB na świeżym syntetycznym PG17 z faktycznymi migracjami007:
1. SIGTERM przed commit natywnych przypomnień: nowy paused do wyjścia poprzednika,
  4 wpisy widoczne dopiero po wspólnym commit, następnie przejęcie bez duplikatów.
2. Kill przed commit:0 częściowych wpisów, nowy przygotowuje4,1 szkic dozwolonego
   klienta, zablokowany job failed/0 szkiców, bez nowych kontaktów/zadań. Kolejny proces
   nie zmienia fingerprintów. Stare API d15265b czyta3 syntetyczne salony bez zmiany
   wszystkich21 tabel. Nie uruchamiano starego workera na tym schemacie.
3. Historyczny Alembic d15265b na007 odmawia: Can't locate revision007. Dane21 tabel
   bez zmian. Zwykły rollback/start d15265b po native migracji jest BLOCKED; nie stosować
   downgrade/stamp004 jako obejścia. Potrzebny osobno zatwierdzony zgodny/API-only start.

Wraz z dwiema wersjami testu pakowania daje to **5 nowych przypadków**. Dotychczasowe
próby legacy→nowy na004 i nowe→nowy na007 są rozdzielone. Żaden test nie dowodzi
rzeczywistego zakończenia starych procesów w Render ani gwarancji exactly-once HTTP.

## Testy lokalne

`DATABASE_URL=<lokalny focus3_test> pytest -q tests/test_release_native_rehearsal.py
 tests/test_runtime_packaging.py tests/test_release_rehearsal.py tests/test_worker_lifecycle.py
 tests/test_release_selects.py tests/test_contact_concurrency.py tests/test_native_pagination.py
 tests/test_supervise.py` — **63 PASS /0FAIL/0SKIP,67.11s**.

Pierwszy zestaw4:2PASS/2FAIL. Test oczekiwał błędu Alembic na stderr, był na stdout;
Docker buildx próbował zapisać metadata do read-only home. Poprawiono przechwytywanie
strumieni i prywatny BUILDX_CONFIG w katalogu testowym, zachowując DOCKER_CONFIG/credentials.
Potem4/4 PASS i po dodaniu negatywnej próby baseline powyższe63 PASS. Nie osłabiono
asercji, nie zmieniono timeoutów dotychczasowych testów. Skasowano tylko własne lokalne
artefakty/DB syntetyczne; brak danych klientów i połączeń z produkcyjną bazą.

Końcowy pełny CI kandydata ma potwierdzić364 testy, build, Chromium/WebKit i oba audyty.
Do takiego wyniku nie deklarować PASS całości024. Workflow i wyłączenie operatorskiego
cleanup są niezmienione. Nie uruchamiano produkcyjnych skryptów ani cleanup.

## Decyzja i dokumentacja

Pełna macierz PASS/BLOCKED, dowodów, luk, ryzyka, czynności i zgód:
`docs/reports/PRODUCTION_READINESS.md`. ROLLOUT_ROLLBACK opisuje wariant004/nowe funkcjeOFF,
STOP przed migracją/bootstrapem, wymagane wyjście starych workerów oraz ograniczenia
rollbacku007. Health i heartbeat nie są dowodem handoff ani RPO.

Nie zamknięto: bieżący SQL/konta, RPO≤60min, trwały magazyn/klucz, artefakt/env rollbacku,
produkcyjny handoff i zgoda wydania. Nie wykazano potrzeby upgrade; najpierw dowód
z istniejącego PITR, potem osobna decyzja o izolowanym płatnym teście. Bez nowej kopii,
production restore/PITR, zmian sieci/sekretów/uprawnień, merge/deploy i nowych kosztów.
Nie aktywowano Meta/DM/Google. Focus1.0/2.0 nietknięte. PR3Draft. Produkcja **BLOCKED**.

Następna bezpieczna luka do sesji025 po zielonym024: bootstrap może odtworzyć techniczne
konto managera z pozostawionego VERIFICATION_PASSWORD, jeśli nie istnieje. WORKER_PAUSED
nie blokuje bootstrapu. Przygotować domyślną blokadę takiego tworzenia i testy tylko na
danych syntetycznych; nie tworzyć/wyłączać żadnych rzeczywistych kont ani sekretów.

Szacunek nadal ≥5 sesji podstawowych +≥1 DM; lokalne testy nie zmniejszają liczby
niepotwierdzonych warunków operacyjnych. Najważniejsza czynność operatora: udostępnienie
zatwierdzonego wewnętrznego kanału READ ONLY. Plan wznowienia i punkty STOP w dokumentach.

Pliki: Dockerfile; tests/test_release_native_rehearsal.py; tests/test_runtime_packaging.py;
docs/reports/PRODUCTION_READINESS.md; dokumenty/evidence session-024; RESUME.md i raport poranny.

## Dodatkowa walidacja podczas oczekiwania na CI

Dla kodu8f3810e wykonano lokalnie `npm run build --prefix frontend` — PASS;
`python -m tests.ci_e2e` — Chromium i WebKit PASS, wraz z offline, CRM, wizytami,
paginacją i fixture błędnej daty pod aktywnym service workerem. Oba audyty lokalne
PASS,0 znanych podatności. Szczegóły bez danych klientów: local-validation.json.
Powód dodatkowego sprawdzenia: oba workflow zablokowane na instalacji przeglądarek,
po zielonym backendzie/buildzie. Aktywny log job129279165990 zwrócił404, więc nie ma
podstaw do wskazania źródła opóźnienia lub zmiany timeoutów. CI nie jest zastąpione
lokalnym wynikiem i024 nadal nie jest oznaczone jako PASS całości.

Odczyt wyłącznie lokalnego help Render CLI2.33 potwierdził brak komendy recovery lub
latest recoverable point. Postgres ma get/list i operacje mutujące, których nie użyto;
ea dotyczy object storage. Nie rozpoczęto logowania ani żadnej sesji CLI do produkcji.
Dostępne narzędzia nie dostarczają brakujących dowodów RPO; potrzebny panel/provider.

## Zamknięcie024 — PASS kodu/testów, produkcja BLOCKED

Dokładny HEAD180d7767b60e7b19c7952a72b76adc824bf71586, workflow PR42653906423 SUCCESS:
https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42653906423 .
Job129287164232:364 PASS/0FAIL/0SKIP,130.19s. Build, Chromium i WebKit oraz oba audyty
PASS;0 znanych podatności.5 nowych przypadków024. Wykonano próby zatrzymania/przejęcia/restartu/rollbacku/pakowania,
bez zastępowania CI lokalnym wynikiem.
Emulacja iPhone, bez nowego testu fizycznego urządzenia. Nie zmieniono workflow/timeoutów.
Workflow push42653874111 dla180d776 również zakończył się SUCCESS.
Starsze uruchomienia8f3810e nie zastępują wyniku dokładnego180d776.

Niezależny kolejny cel025 można rozpocząć: usunięcie automatycznego odtwarzania
technicznego managera przez bootstrap. Nie zamyka to bieżącego konta/sesji w produkcji.
