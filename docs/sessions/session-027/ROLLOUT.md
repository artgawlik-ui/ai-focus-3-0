# Plan027 — przygotowany, niewykonany

## Cel i zakres

Najpierw kandydat3.0.4 na zatwierdzonym004, nowe moduły OFF. Native007 jest oddzielną
ścieżką wymagającą zgody na migrację i rozszerzone odczyty; zgoda A pozostaje004/17tabel.
Nie łączyć profilu Google005 z native007. Nowy `Dockerfile.rollback` dotyczy wyłącznie
awaryjnego API-only/read-only na007, nie zastępuje pełnej aplikacji ani restore.

## Bramka przed jakąkolwiek operacją

Każdy brak oznacza STOP: pełne CI konkretnego SHA; aktualny SQL004/17 i prywatne konta;
RPO≤60min; świeża zaszyfrowana kopia z niezależnym kluczem i dowodem odzyskania;
zatwierdzony zgodny artefakt/start/env rollbacku; zgoda na plan i okno niedostępności zapisów.
Nie wystarcza historyczny dump1listopada, sam status available lub commit w Git.
Nic poniżej nie zostało wykonane na Render, koncie lub rzeczywistych danych.

## Przełączenie starego d15265b — czynności później wykonywane przez operatora/agenta po zgodzie

1. Właściciel zatwierdza SHA,004 versus osobne007, okno maintenance, oczekiwane skutki
   starych jobów/retencji oraz powrót. Potwierdzić autoDeploy=no i jedną instancję.
2. Po osobnej zgodzie w Render → ai-focus-3-0 → Settings → Maintenance Mode włączyć
   standardową stronę. Oficjalna dokumentacja potwierdza tę funkcję dla płatnych web services,
   więc nie wymaga z założenia nowego planu. Potwierdzić publiczne503 i opróżnienie
   wcześniejszych żądań. **Maintenance nie zatrzymuje prywatnego ruchu, SSH ani workera.**
   Zatrzymać inne źródła zapisów; jeśli nie można tego udowodnić — STOP.
3. Nie zakładać, że WORKER_PAUSED lub MetaOFF wycisza staryd15265b: ignoruje nową pauzę,
   a retencja jest niezależna. Dopuszczone stare joby mogą jeszcze commitować aż do wyjścia.
   Jeśli wymagany jest całkowity freeze przed backupem, brak dowodu zatrzymania starego
   procesu oznacza STOP i osobną decyzję o kontrolowanym downtime, bez improwizacji.
4. Nowy proces ma startować z API niedostępnym dla zapisów publicznych i nowym workerem
   w pauzie. Bez zmiany standardowego obrazu można **później** zatwierdzić Docker command:
   `sh -c 'umask 077; : > /tmp/focus3-worker.pause; exec sh scripts/start.sh'`,
   z WORKER_PAUSED=false. Plik jest obecny przed startem dzieci. Każdy restart z tym
   override ponownie pauzuje pracę — fail-closed, ale wymaga nadzoru operatora.
   Alternatywa WORKER_PAUSED=true również pauzuje, lecz usunięcie pliku wtedy NIE wznawia
   pracy; zmiana env wymaga kolejnej osobnej operacji. Wybrać i zatwierdzić jedną metodę.
5. `start.sh` uruchamia Alembic i ewentualny bootstrap PRZED supervisorem. Pauza tego
   nie blokuje. Na004 najpierw dowód, że upgrade jest no-op i konta już istnieją;
   nie uruchamiać007 jako skutku ubocznego flagi. Jeśli potrzebna migracja — STOP do
   oddzielnego planu, kopii, testu na kopii i zgody; nigdy downgrade/stamp dla obejścia.
6. Po zatwierdzonym deployu nowy worker ma status paused. Po zdrowiu nowej instancji
   Render kończy starą: supervisor daje25s na zakończenie, potem kill. Udowodnić wyjście
   KAŻDEJ starej instancji/procesu przez oficjalne zdarzenia i autoryzowany Shell.
   Nowyhealth, PID lub heartbeat nie są dowodem zniknięcia starego konsumenta.
   Niewyjaśniony stary proces lub restart starego kodu = STOP; nowy pozostaje paused.
7. Przed wznowieniem skontrolować zatwierdzony zakres SQL. Przerwany legacyjob running
   odzyska się po5min; nie robić ręcznego UPDATE. Porównać kolejkę/inbox/retencję i count/hash.
   Zmiany od zatwierdzonej starej pracy wymagają udokumentowanego uzgodnienia; nie udawać
   identycznych fingerprintów przy aktywnych zapisach. Nieznane ubytki/duplikaty = STOP.
8. Weryfikować SHA, tryb startu i efektywne flagi bez wartości sekretów. Meta legacy i
   wszystkie niezależne moduły/OAuth/webhook/ingest/DM OFF; Google i płatne AI OFF;
   offsite/retencja/diagnostyka/native w stanie jawnie zatwierdzonym, nie domyślnie zgadniętym.
9. Dopiero po osobnej zgodzie wznowić nowy worker, np. usunąć lokalny plik pauzy,
   jeśli wybrano wariant z WORKER_PAUSED=false. To operacja zapisu/sterowania,
   NIE część zgody A. Obserwować jeden konsument, zmiany queued/running/completed,
   brak duplikatów i szkiców opt-out, poprawne przypomnienia. STOP przy błędzie.
10. Po kontrolach właściciel zezwala na wyłączenie public maintenance. Zapisz dowody
    przed/po, czas, SHA i operatora bez danych klientów. Restart w modelu z override
    znów pauzuje worker; nie obiecywać bezobsługowego wznowienia po awarii.

## Wariant rollbacku007 — ograniczony tryb awaryjny

Źródło: gałąź027 z runtime odziedziczonym po zielonym e37ce5d. Budowa później wyłącznie
z zatwierdzonego SHA i `Dockerfile.rollback`, z zachowaniem digestu/artefaktu. CI zbudował pełny obraz testowy, lecz go nie uruchamiał ani nie publikował;
nie zachowano go jako artefaktu rollbacku Render. Nie uruchomiono nowej usługi
Render i nie zmieniono konfiguracji produkcyjnej. Budowa testowa nie zamyka tej bramki.

Obraz nie pakuje migracji, bootstrapu, supervisora ani offsite skryptu. Startuje wyłącznie
`scripts.rollback_readonly`. Brak dokładnie `FOCUS_READONLY_ROLLBACK_APPROVED=true`
kończy proces. Zawsze wymaga PG17, rewizji007 i dokładnego zestawu21tabel. Każde połączenie
ma default_transaction_read_only=on, timeout zapytania5s/lock1s. Wszystkie integracje
wyłączone przed importem API. Nie startuje worker, nie tworzy kont/sesji ani backupu.

To świadoma degradacja: tylko GET/HEAD zdrowia, bieżącej sesji, salonów/historii,
legacywizyt i dashboardu; root pokazuje stan read-only. Pozostałe ścieżki i wszystkie
zapisy (w tym login/logout i eksport)503. Dotychczasowe ważne sesje i RBAC pozostają;
nowe logowanie niedostępne, wygasła sesja401. Natywny kalendarz/zadania i UI nie są
udawane jako działające w tym profilu. Nie jest to pełny rollback funkcjonalny.

Po osobnej zgodzie: maintenance → pauza/drain wszystkich nowych workerów → dowód wyjścia
→ zatwierdzony obraz awaryjny/start/env → kontrola007/21 zgodnie z NOWĄ zgodą, nie A
→ gotowość i istniejąca sesja → ewentualna decyzja o udostępnieniu odczytu.
Brak obrazu, niezgodny schemat lub brak akceptacji utraty zapisów/logowania = STOP.
Nie klikać Rollback do d15265b na007: jego domyślny Alembic odrzuca007, a snapshot może
włączyć starego workera. Nie wykonywać downgrade/DROP/stamp, restore lub zmiany DATABASE_URL.
Powrót z trybu awaryjnego do normalnego jest kolejnym zatwierdzonym wydaniem.

## Gotowość funkcjonalna a testy rzeczywiste

Normalny kandydat ma wcześniejszy CI380PASS: login/logout, RBAC/CSRF, CRM/zapis/historia,
lejek, legacywizyty, nativekalendarz/zadania/raporty, worker i PWA/WebKit.
Nie oznacza to aktywności native007 na obecnej produkcji004. Nowy CI027 potwierdza regresję;
nie wykonywać ponownie dawnych ręcznych symulacji w zastępstwie odczytu produkcji.

Po przyszłej zgodzie produkcyjnej: owner loguje się sam (sesja zapisuje dane, więc nie
jest odczytem); sprawdzić widoki i role. Testy zapisów CRM/lejka/wizyt/zadań wykonywać
na izolowanych danych syntetycznych. Na produkcji nie tworzyć fikcyjnego klienta ani
technicznego managera; realne zamierzone działanie właściciela wymaga odrębnego zakresu.
Publiczny manifest/ikony/offline można sprawdzić po wydaniu bez danych CRM; WebKit nie
jest fizycznym iPhonem. Wyłączenie konta technicznego i jego sesji potwierdza tylko
zatwierdzony aktualny odczyt, nie udany test na syntetycznej kopii.

Źródła HTTP200 i przeczytane9listopada2026:
https://render.com/docs/maintenance-mode.md (public503, prywatny ruch pozostaje),
https://render.com/docs/rollbacks.md (artefakt/start/env celu),
https://render.com/docs/postgresql-backups.md (PITR,7dni eksportu),
https://render.com/docs/private-network.md (region/workspace/izolacja).
