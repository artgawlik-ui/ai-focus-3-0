# Wydanie 3.0.4 z Meta OFF — plan, niewykonany

## A. Minimalne odczyty

`SELECTS.sql` zawiera dokładnie cztery SELECT-y z parametrami psycopg;
`SELECTS.psql` to równoważny wariant z prywatnymi promptami psql.
Nie wklejać wariantu z %(...) bezpośrednio do psql. Nie wpisywać ID/e-maili do raportu.
Nie zgadywać identyfikatorów kont po nazwie: właściciel zatwierdza oba ID prywatnie.
Brak IDs oznacza not checked, nie PASS. Tylko SELECT-y, BEGIN/SET LOCAL/ROLLBACK;
żadnego bootstrapu, migracji, aplikacji ani workera.

Oba warianty: REPEATABLE READ READ ONLY, UTC, statement timeout 5 s, lock 1 s,
idle transaction 10 s. Opakowanie połączenia powinno dodatkowo ustawić connect timeout
5 s i default_transaction_read_only=on. Nie umieszczać URL/hasła w argumentach programu.
Zapytania są stałe, tabele z białej listy. SQL przygotowano/testowano lokalnie, nie wykonano w produkcji.

1. **baseline:** oczekiwane read_only=true, repeatable_read=true, PG major 17,
   revisions=['004'], 17 tabel, no_unknown_tables=true, constraints_validated=true.
   Flaga constraints_validated to stan katalogu, nie niezależne ponowne sprawdzenie
   każdej relacji. Różnica lub błąd -> STOP i osobna ocena struktury.
2. **accounts:** distinct_approved_accounts, owner_active_manager i technical_disabled
   muszą być true; technical_sessions_total=0 i valid=0. Nie jest to dowód logowania
   właściciela ani zgoda na wyłączenie konta. Brak tożsamości -> STOP, nie reset hasła.
3. **fingerprints:** 17 wierszy, table_name/row_count/sha256, bez treści rekordów.
   Algorytm: SHA-256 z posortowanego w COLLATE C to_jsonb(row)::text, UTF-8, separator LF.
   To **inny format** niż kanoniczny JSON Pythona w scripts.backup.fingerprint oraz COPY hash
   z restore-verification.json. Nie porównywać hashów z różnych algorytmów.
   Ten sam SELECT należy uruchomić w zatwierdzonej odtworzonej kopii oraz w produkcji,
   a przed/po deployu użyć tego samego algorytmu i PG17. Hashe przechowywać kontrolowanie;
   są metadanymi pochodzącymi z danych, nie dowodem anonimizacji.
   Suma 23 jest punktem odtworzonego eksportu, **nie oczekiwaną stałą bieżącej produkcji**.
4. **worker:** liczby queued/running, pending/processing/failed/DLQ i kandydatów retencji.
   Puste znaczniki retencji lub błąd parsowania -> STOP. Odczyt nie wykonuje retencji.
   Obliczenia czasu są timestamptz w UTC, bez błędnego porównania 'T' z odstępem w tekście.
   Liczniki to predykcja zakresu, nie ślad rzeczywistego uruchomienia workera.

Dostęp hosted MCP jest blokowany przez pustą publiczną allowlistę. Nie otwierać jej.
Właściciel ma zatwierdzić wewnętrzny Shell/SSH istniejącej usługi i ograniczony dostęp
wykonawcy (w tym grant TCP, jeśli używany). Potem agent może wykonać odczyty za niego.
Jeżeli wybierze własny Render Shell, może użyć SELECTS.psql po bezpiecznym skonfigurowaniu
istniejącego klienta z wewnętrznego DATABASE_URL, bez wypisywania sekretów.
Transfer narzędzi/SQL do prywatnego katalogu także musi być objęty zgodą; bez instalowania
pakietów czy deployowania gałęzi tylko po to, aby dostarczyć narzędzie.
Brak klienta/znanego host key/uprawnień -> STOP. Istniejący runbook: session-003/ACCESS_RUNBOOK.md.

## B. Ryzyko workera i retencji

AGENT_V2_ENABLED=ON to rozszerzona analiza, **nie kill switch**. Przy ON i OFF worker
przetwarza kolejkę i zapisuje statusy/wyniki/Activity. Maintenance może czyścić treści
wiadomości po 30 dniach, ich rekordy po 90 dniach i wygasłe OAuth state; inbox done
traci payload po 7 dniach i rekord po 90 dniach. Meta OFF nie zatrzymuje retencji.
Nie wykonywano żadnej z tych operacji w produkcji w sesji 005.

Przy zero-downtime stare i nowe procesy mogą działać równolegle. SKIP LOCKED/statusy/lease
ograniczają podwójne pobranie zadań, ale nie dają globalnej ciszy zapisów. Restart/przerwanie
może zostawić running do odzyskania po 5 minutach. Retencja jest idempotentna, lecz może
zmienić liczności/hashe i konkurować o blokady podczas migracji lub porównania.
Brak nowej migracji 3.0.4 względem d15265b zmniejsza ryzyko, ale start.sh wywołuje alembic
upgrade head i supervisor uruchamia workera. Nie uruchamiać ich do preflightu.

**Właściciel musi wybrać przed wydaniem:**
- zaakceptowany kontrolowany tryb istniejących szkiców/retencji i jawne rozliczenie każdej
  zmiany między manifestami, albo
- zatwierdzone okno bez zapisów, obejmujące API, kolejkę i maintenance. Obecny AGENT_V2=OFF
  tego nie zapewnia; ewentualna pauza/zmiana procesu lub nowy mechanizm wymaga odrębnej zgody.
Nie wolno ignorować całych tabel sesji/jobów, żeby wymusić zgodność. Niewyjaśnione różnice -> STOP.
Transport DM jest niezależnie OFF/niezaimplementowany; testy nie stanowią zgody na komunikację.

## C. STOP przed zatwierdzeniem wydania

- Brak aktualnego SQL, niezgodne 004/tabele/konta lub niewyjaśnione hashe.
- Brak zaakceptowanego RPO. Eksport z 19:25 Warszawa jest odtwarzalny, ale o kilka godzin
  starszy od kontroli; bez porównania z produkcją nie jest dowodem pełnej aktualności.
- Brak trwałej szyfrowanej kopii/niezależnego klucza/retencji i testu odzyskiwania klucza.
- Brak potwierdzenia artefaktu rollbacku lub nieznana konfiguracja target deployu.
- Jakakolwiek flaga Meta/DM ON, nieustalona aktywność workera lub brak obsługi trwających jobów.
- Brak zielonego CI dokładnego SHA lub osobnej zgody na merge/deploy.

## D. Kolejność przyszłego zatwierdzonego wydania

1. Odczytać HEAD i checks. Zapisać live d15265b / dep-dbjhl6jbc2fs73crj65g oraz dostępność
   artefaktu i jego środowiska; dzisiejsze API env-vars nie jest snapshotem rollbacku.
2. Wykonać A w uzgodnionym trybie B; porównać manifest wszystkich 17 tabel i konta.
3. Zapewnić backup zgodny z zatwierdzonym RPO, szyfrowanym trwałym magazynem i odrębnym kluczem;
   test restore izolowany, bez aplikacji. Nowy eksport/zmiana retencji nie są objęte sesją 005.
4. Po osobnej zgodzie merge i deploy konkretnego SHA istniejącej usługi, Meta OFF.
   Żadnej nowej płatnej instancji, niezatwierdzonej migracji ani cleanup salonu.
5. Po deployu: Render live status i rzeczywisty SHA, HTTPS/health, wersja 3.0.4, API 401,
   owner login/logout, nieaktywne konto techniczne i brak jego sesji; flagi Meta/DM nadal OFF.
   Login może sam zmienić sessions/login_attempts — moment porównania musi to uwzględniać.
6. Powtórzyć A przed testami zmieniającymi sesje lub rozliczyć je jawnie; niewyjaśniony drift -> STOP.
   Nie tworzyć testowych klientów na produkcji. Mobilny smoke/PWA bez cache danych CRM.
7. Przy awarii: tylko zatwierdzony rollback kodu, nigdy automatyczny restore DB/DROP/downgrade;
   kopia nie może przywrócić wycofanych zgód, usuniętych treści i ważnych starych sesji.
   Bez dostępnego artefaktu osobno zatwierdzony rebuild sprawdzonego SHA, nie zgadywany target.

W tej sesji żaden z kroków wdrożeniowych, pauz ani zmian konfiguracji nie został wykonany.
