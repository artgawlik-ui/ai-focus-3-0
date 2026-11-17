# RAPORT AI FOCUS 3.0.4 — SESJA 004: gotowość wydania

Data: 1 listopada 2026, Europe/Warsaw. **Decyzja: BLOCKED.**
Kod i regresja aplikacji mają dowody lokalne, ale brakuje aktualnego odczytu schematu
produkcji i świeżego potwierdzonego punktu odzyskiwania. Nie wykonano wdrożenia.

## Repozytorium i PR

Gałąź fix/3.0.4-meta-validation, PR #3 open/Draft/niepołączony.
Bazowy HEAD 935acab1b9fb42b96ea6168c662301d612d61ec9. Obie kontrole odczytano:
PR 41323445481 i push 41323441894 — success, dla tego samego SHA.
Aktualna baza PR/origin/main: d15265b26524d594bdbcb4bc6b63fcbc398a1424.
Lokalny ref main był starszy (ba951fd), więc porównania skorygowano do origin/main;
fetch bez merge/reset/push main. Historyczne diff-main ze starszych raportów nie
stanowią dowodu braku zmian schematu względem bieżącej bazy PR.

40eb69f: kryteria przed testami i jawne wyłączenie operatorskiego cleanup z CI.
Pozostałe zmiany tej sesji to dokumentacja i dowody; SHA raportu w git log katalogu.
Nie znaleziono regresji aplikacji wymagającej zmiany kodu backendu/frontendu. Dodano testy semantyki agenta i integralności kopii aplikacji; szczegóły FINAL_REVIEW.md.

## Schemat i dane

- git diff origin/main -- backend/db.py backend/meta_models.py migrations: pusty wynik.
- python -m alembic heads: 004 (head).
- test_meta_migration wykonany w pełnej regresji na świeżej lokalnej bazie: upgrade,
  powtórka i zachowujący dane rollback/re-up; bez produkcyjnych migracji.
- test_synthetic_recovery: szyfrowany backup/restore syntetycznego PostgreSQL i zgodność
  17 tabel, bez zmiany źródła, w ramach pełnej regresji.
- Render PostgreSQL available, wersja 17, Frankfurt, publiczna allowlista pusta.
- SELECT bieżącej revision/liczby tabel przez narzędzie READ ONLY odrzucony przed
  połączeniem: hosted MCP nie ma dopuszczonych adresów. Nie zmieniano allowlisty,
  nie próbowano obejścia, nie wykonano DML ani cleanup.
**PASS lokalnie** dla zgodności kodu z 004, **BLOCKED** dla aktualnego schematu produkcji.

## Testy i audyty — nowe wykonanie

Dokładne agregaty/komendy w evidence.json.
- Backend i API: początkowo 134 passed; po dodaniu 6 niezależnych testów bezpieczeństwa **140 passed, 0 failed/errors/skipped**, 47,37 s.
- Wyłączono z kolekcji **11 testów operatorskiego cleanup** przez
  --ignore=tests/test_salon_cleanup.py, zgodnie z bieżącym zakazem uruchamiania tych
  skryptów. Nie uruchomiono skryptu DELETE/cleanup, także przez automatyczny CI.
  Nie przedstawiamy tego jako uruchomienia testów operatorskich; pełna regresja aplikacji nie obejmuje
  odrębnych narzędzi usuwania salonu. Pomocnicze fixture tworzą wyłącznie dane syntetyczne.
- npm run build --prefix frontend: PASS.
- python -m tests.ci_e2e: Chromium desktop PASS, WebKit/iPhone emulowany PASS.
- pip-audit -r requirements.txt: 32 zależności, **0 znanych podatności**.
- npm audit --prefix frontend: **0 podatności**.
- Dwa znane ostrzeżenia pytest/Starlette. Nie przeprowadzono nowego testu fizycznego iPhone'a.
Testy PostgreSQL uruchamiano sekwencyjnie. Nie uruchomiono start.sh na produkcji.
Końcowy CI nowego HEAD należy odczytać w Checks PR #3; bazowy wynik nie jest jego substytutem.

## Render — aktualne odczyty bez zmian

Potwierdzono wcześniej wskazane My Workspace; dokładne identyfikatory i metadata
w render-readonly.json. MCP get_service/list_deploys/get_deploy/get_postgres wyłącznie GET.
Live: **d15265b**, deploy **dep-dbjhl6jbc2fs73crj65g**, aplikacja publiczna **3.0.3**.
Repo i main zgodne; autodeploy no; jedna instancja 0.5c/512 MB, /api/health.
Publiczne GET: health 200, auth/me/salons/meta/status 401, OAuth callback/webhook 404;
API no-store i HSTS. Nie wykonano logowania, POST callbacka, OAuth ani dostępu do klientów.

MCP nie ma odczytu env-vars; oficjalny CLI v2.33.0 nadal uwierzytelniony w tym samym
workspace. Wykorzystano istniejący profil CLI wyłącznie do uwierzytelnienia odczytowego
API, bez wyświetlenia/persistowania sekretu. Odczytano tylko flagi, bez BOOTSTRAP_PASSWORD,
tokenów Meta i danych połączenia. Nie uruchamiano login ani zmiany konfiguracji.

- META_ENABLED OFF; OAuth, webhook verify, ingest, CRM history i diagnostics są
  nieustawione i dziedziczą OFF. DM transport nieustawiony, niezależnie OFF.
- Grupy środowiska workspace: 0. Brak dodatkowego dziedziczenia z env groups.
- AGENT_V2_ENABLED **ON już przed tą sesją**, AI_PAID_PROCESSING_APPROVED OFF.
  Kod AGENT_V2 steruje rozszerzoną analizą, a nie uruchamianiem procesu workera;
  worker istnieje i generuje szkice z kolejki. Nie włączono nowej automatyzacji.
  Transport DM pozostaje niewdrożony i zablokowany wewnętrznie; nie ma automatycznej wysyłki. Worker nadal może automatycznie zapisywać zadania/szkice i wykonywać retencję także przy Meta OFF i AGENT_V2 OFF; flaga nie jest kill switchem. Nie wykonywano tych operacji na produkcji w tej sesji.
- OFFSITE_BACKUP_ENABLED OFF; nie potwierdza to stanu niezależnych kopii/PITR Render.

configuration-status.json opisuje zapisane bieżące ustawienia API. Nie jest migawką
środowiska działającego procesu ani target deployu rollback; publiczne 404 potwierdzają
zamknięcie badanych wejść OAuth/webhook. Podpisane callbacki prywatności mają osobną
semantykę i nie są transportem komunikacji. Nie wywoływano ich.

## Rollback

Punkt wyjścia potwierdzono odczytem jako live; plan w ROLLBACK.md. Odczytano bieżące
oficjalne deploys.md, health-checks.md, rollbacks.md i cli.md (HTTP 200).
Samo istnienie deployu nie daje dowodu przyszłej dostępności zachowanego artefaktu;
API nie ujawnia osobnej eligibility flag. Rollback nie odtwarza bazy, a zmienne środowiska
pochodzą z target deployu — dzisiejsze wartości nie zastępują tej kontroli.
Aktualna świeża zaszyfrowana kopia, trwały klucz/retencja, test restore oraz konta produkcyjne
nie zostały potwierdzone w tej sesji; nie czytano historycznych kopii/plików sesji CRM.

## Rzeczywiste blokady przed wydaniem

1. **Bieżący schemat SQL**: brak dostępnego wewnętrznego read-only kanału; hosted MCP
   blokuje pusta allowlista, a granty TCP środowiska są puste. Wymagany zatwierdzony
   SSH/Shell istniejącej usługi i ograniczony grant, bez publicznego otwierania bazy.
2. **Recovery i konta**: potrzebna aktualna zaszyfrowana kopia z trwałym kluczem i test
   restore, sprawdzenie konta technicznego/sesji i właściciela. Dowody syntetyczne nie
   potwierdzają ich bieżącego stanu. Nie wykorzystywano historycznych cookies właściciela.
3. **Rollback/środowisko runtime**: przed wydaniem sprawdzić dostępność artefaktu,
   schemat i faktyczne środowisko rollbacku; zatwierdzić zachowanie istniejącego agenta ON.
   Nie zmieniano agenta, flag ani konfiguracji dla wymuszenia zgodności.
4. **Automatyczne zapisy workera**: jeśli warunkiem jest brak wszelkich automatycznych zapisów, aktualny kod/AGENT_V2 tego nie zapewnia. Potrzebna decyzja o akceptacji obecnego trybu szkiców/retencji lub osobna zmiana; nie modyfikowano konfiguracji.
5. **Osobne zatwierdzenie merge/deploy** pozostaje warunkiem wykonania, nie wadą kodu.
   Nie uruchamiać start.sh przed sprawdzeniem 004: zawiera alembic upgrade head i worker.
Meta nie jest potrzebna do wydania z Meta OFF i pozostaje nieaktywna; nie utożsamiamy
braku prawdziwego testu Instagrama z błędem CRM. Cleanup salonu jest poza zakresem.

## Bezpieczeństwo, zakres i wznowienie

Nie zmieniono danych klientów, sekretów, uprawnień, sieci, planów ani zasobów.
Bez produkcyjnych migracji, DELETE/cleanup, merge, deploy, restartu, aktywacji Meta,
OAuth/Graph/DM i nowej automatycznej wysyłki. Bez płatnych zasobów.
Focus 1.0/2.0 nietknięte; zmiany tylko w tym repozytorium; diff-base.txt względem
rzeczywistego origin/main, nie starego ref main. Oryginalne archiwa nieśledzone nietknięte.
Pozostaje **5 sesji podstawowych + ≥1 DM**, licznik bez zmian: pełna bramka operacyjna
nie została zamknięta. Wznowić od odczytu HEAD/checks i zatwierdzonego kanału SQL;
nie ponawiać zamkniętych testów bez zmiany kodu/przyczyny. Nie działamy w tle po sesji.
