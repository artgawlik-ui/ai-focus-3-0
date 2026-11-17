# Wydanie024 — plan niewykonany, z punktami STOP

**Cel:** kontrolowany kandydat3.0.4 na obecnym schemacie004, wszystkie nowe moduły OFF.
Opcjonalny native007 jest przetestowany lokalnie, ale NIE jest objęty zgodą A ani zgodą
na migrację. Nie łączyć schematów Google005 i native006/007. Google poza zakresem.

## Warunki wstępne — każdy brak oznacza STOP

- Osobna pisemna zgoda na merge, konkretny SHA i deploy; PR #3 pozostaje Draft do decyzji.
- Pełny CI SHA, zatwierdzony zakres schematu, aktualne4SELECT-y004/17 i prywatne konta.
- Rzeczywisty punkt recovery w RPO≤60 min, jego trwałość/odtwarzalność i niezależny klucz.
- Zatwierdzony backup przed wydaniem i dowód restore; aktualna sesja nie tworzy kopii.
- Zachowany artefakt rollbacku, przegląd jego env/startu, kontrola starych procesów.
- Jawnie sprawdzone efektywne flagi. META_ENABLED i wszystkie niezależne META_OAUTH,
  WEBHOOK_VERIFY,INGEST,CRM_HISTORY,DIAGNOSTICS,DM_TRANSPORT_ENABLED=false.
  Nie polegać tylko na legacy META_ENABLED. Google/płatne AI/offsite oraz FOCUS_CALENDAR,
  FOCUS_CALENDAR_SCHEMA i FOCUS_DIAGNOSTICS_ENABLED OFF. To wymagania, nie deklaracja
  odczytu aktualnych wartości produkcyjnych. W tej sesji nie pobierano sekretów/env.

## Pierwszy handoff z d15265b

1. Po zgodzie nowe procesy muszą startować z WORKER_PAUSED=true. Pauza nie zatrzymuje
   starego d15265b, API ani osobnego backup-processu. AGENT_V2_ENABLED nie jest pauzą.
   Meta OFF nie zatrzymuje istniejącej retencji w starym workerze.
2. Skrypt start.sh najpierw uruchamia Alembic i opcjonalny bootstrap, dopiero supervisor.
   WORKER_PAUSED nie blokuje tych czynności. Bez zatwierdzonego planu ich wykonania/
   bezpiecznego pominięcia → STOP. Nie zakładać, że marker004 oznacza zgodę na startup DML.
3. Przed wznowieniem nowego workera uzyskać dowód zakończenia KAŻDEGO starego procesu
   przez autoryzowany kanał/zdarzenia Render. Nowy health/PID/heartbeat nie dowodzi tego.
   Przy pierwszym rolling deploy nie wolno pozostawić równoległego d15265b i aktywnego
   nowego konsumenta; starego nie chronią nowe blokady.
4. SIGTERM kończy bieżący etap; supervisor po25s wymusza kill. Długie HTTP może przekroczyć
   budżet. Przerwany job pozostaje running i odzyskuje się po5min; bez ręcznego UPDATE.
   Utrata transakcji natywnej oznacza rollback całości i ponowne przygotowanie przypomnień.
5. Dopiero po zatwierdzonej kontroli SQL/kolejki i wyjściu starego kodu osobno zatwierdzić
   wznowienie nowego workera. Plik pauzy jest lokalny; nie jest rozproszonym przełącznikiem.
6. Kontrole po wdrożeniu: faktyczny SHA/health, efektywne flagi, stan wszystkich procesów,
   odzyskane/przetworzone joby, brak duplikatów/nowych szkiców dla opt-out, zakres A004/17,
   uzasadnione różnice count/hash. Właścicielskie operacje/API mogą zmieniać dane — nie
   ogłaszać identyczności snapshotów przy aktywnych zapisach. Nie rozszerzać A do native.

## Co potwierdza nowa próba syntetyczna

Rzeczywisty PG17, faktyczne migracje do007,21 tabel, dane wyłącznie syntetyczne.
Pierwszy worker startuje paused; zatrzymano go przed commit przypomnień. Nowy pozostaje
paused do potwierdzenia wyjścia starego. SIGTERM+drain:4 przypomnienia commitują razem;
kill:0 częściowych wpisów. Następnie przejęcie,1 szkic aktywnego klienta,0 dla zablokowanego,
4 unikalne przypomnienia, bez nowych kontaktów i zadań. Kolejny proces nie zmienia danych.
Stare API d15265b w trybie wyłącznie odczytu zachowuje fingerprinty wszystkich21 tabel.
To nie test faktycznego deployu ani produkcyjnego handoff; testuje nowy protokół.
Legacy→nowy na004 ma osobne istniejące testy z sesji012; oba zestawy są w regresji024.

## Rollback — dwie różne ścieżki

### Schemat004, moduły OFF

Odczyt Render potwierdził d15265b / dep-dbjhl6jbc2fs73crj65g live. API nie ujawnia
eligibility artefaktu ani snapshotu env. Git commit ≠ zachowany obraz. Przed zatwierdzeniem
powrotu sprawdzić Dashboard → ai-focus-3-0 → Deploys → dostępność Rollback i konfigurację
celu, bez uruchamiania. D15265b nie zna nowej pauzy; najpierw wyciszyć nowe procesy,
nie wznawiać starego konsumenta bez zatwierdzonej kontroli kolejki/retencji.

### Jeżeli kiedykolwiek zatwierdzono native006/007

Test prawdziwego historycznego Alembic d15265b na007 zwraca błąd:
`Can't locate revision identified by '007'`. Standardowy start starego obrazu NIE jest
bezpieczną ścieżką powrotu. Nie naprawiać tego downgrade/DROP/stamp004 na produkcji.
Odczyt starego API działa tylko po świadomym pominięciu starej migracji/startu workera.

Potrzebna osobna decyzja: zachowany zgodny artefakt3.0.4 albo zatwierdzony rebuild/API-only
ze starego SHA, ze sprawdzonym startem bez Alembic/bootstrap/workera. Nie wykonywać
jednego kliknięcia Rollback przy założeniu, że dzisiejszy override się zachowa.
Render przy rollbacku odtwarza Docker command/start command i env celu; env groups mogą
mieć dzisiejsze wartości. Zmiana obecnej konfiguracji nie dowodzi ustawień rollbacku.
W obu ścieżkach brak automatycznego fallbacku, restore, przełączenia DB i zmian danych.

Źródło odczytane2026-11-09: https://render.com/docs/rollbacks.md .

Uzupełnienie025: nowy bootstrap nie odtwarza kont technicznych i pomija provisioning
przy istniejących użytkownikach. Nie jest to poprawka starego obrazu d15265b ani dowód
wyłączenia konta produkcyjnego. Migracja/start/env targetu wciąż wymagają przeglądu.
