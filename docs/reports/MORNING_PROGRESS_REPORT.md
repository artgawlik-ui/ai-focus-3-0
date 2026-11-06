# Raport poranny Ai Focus3.0.4 — 2026-11-06 (Europe/Warsaw)

## Ukończony zakres i punkt wznowienia

Sesje017–020 ukończone i zweryfikowane wCI;021 ma testy lokalne, czeka na pełneCI. Sesja016 została zamknięta po nowej decyzji
właściciela: rezygnacja z dalszej integracji Google Calendar. Nie deklarujemy jej napraw
lub testuGoogle live. Nowy kierunek to natywny Focus, bez kasowania kodu/tabel/danych005.
Ostatni commit kodu7afb5bffaa11f4549f7f7a1d695b38bc38d36493; końcowy dopisek dokumentacyjny
jest oddzielnym commitem i również wymaga zielonegoCI wChecksPR3.
PR3Draft: https://github.com/artgawlik-ui/ai-focus-3-0/pull/3.
RESUME.md zawiera plan kolejnego etapu. Nie ma deklaracji działania w tle po zakończeniu.

## Rzeczywiście dodane funkcje

- Natywny kalendarz wykorzystuje dotychczasowe appointments: dzień/tydzień/miesiąc,
 tworzenie/edycja/anulowanie, dotychczasowe sprawdzanie konfliktów i powiązanieCRM.
- Monitoring rzeczywistych kontaktów: progi7/14/30/60, indywidualny okres1–365 dni
 per salon i per priorytet, A+/A pierwsze. Brak kontaktuNULL, osobno wiek rekordu.
 Szkic, task, follow_up o niejednoznacznej semantyce i plan wizyty nie resetują licznika.
- Trwałe, deduplikowane zadania, priorytety, wynik, cykle i rozdział deklaracji kontaktu
 od wykonania taska. Rzeczywisty kontakt wymaga jawnego wyboru rodzaju i wyniku.
- Wewnętrzne centrum powiadomień, konfigurowalne przypomnienia wizyt, odczyt ustawień,
 pojedynczy aktualny próg i obsługa zmiany terminu/odwołania/opiekuna. Nie ma webpush.
- Raport dnia, okna2h/24h od teraz, zadania zaległe i jawne ryzyko (nierozpoczęte do2h),
 managerfilter, kontakty odnotowane i terminowość. Brak wpisu zakończenia wizyty nie
 jest przedstawiany jako dowód jej nieodbycia. Raporty zawierają moment wygenerowania.
- Datetime-local wWarszawie, walidacja lukiDST i jawne rozróżnienie godziny jesiennej;
 rewizje przeciw nadpisaniu, szczegółowy audyt starego/nowego terminu i wykonawcy.
- RBAC aktualnego opiekuna, opt-out, blokady kontaktu i rekorduSalon. Worker używa
 istniejącego procesu, respektuje pauzę/stop, nie wykonuje komunikacji z klientami.

## Naprawione problemy

Nowy router przeniesiono przed SPA. Poprawiono fixture UTC/DST i zakres danych
syntetycznych. Dodano jednoznaczneARIA do select kontaktu i wyboru klienta poFAIL
pierwszegoE2E019. Oddzielono przełącznik schematu od runtime, aby featureOFF nie
blokował startu po006. Stare przypomnienia są filtrowane po zmianie terminu/opiekuna.
Audyt zachowuje obie daty. FaktycznySIGKILL przedcommit nie zostawia częściowych zapisów.

## Komendy i wyniki

**45 nowych przypadków od015:25w017+9w018+4w019+3w020+4w021. Ostatni potwierdzony pełnyCI:300PASS(020).**
-017 ad348f0045529a6fa2170b54a69df4f3177d034f — CI42302108082 SUCCESS/284PASS.
-018 8c64fa0ec9189aa95d8e14929f0106f6ede1e649 — CI42303042647 SUCCESS/293PASS.
-019 cb01fd8bb0574362ee1721fa3d061e83dfbe22a4 — CI42304747622 SUCCESS/297PASS.
-020 7afb5bffaa11f4549f7f7a1d695b38bc38d36493 — CI42305590784 SUCCESS/300PASS:
 https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42305590784.
Każdy z tychCI: build, chromium-desktop, webkit-iphone, npm audit i pip-auditPASS,
0 znanych podatności. Pełny workflow wykonuje pytest bez11 operatorskich cleanup.
Krytyczne nowe funkcje nie są pomijane. Nie mierzono procentowego coverage.

Lokalnie syntetyczny PostgreSQL17/256MB/1CPU: pytest -q tests/test_native_planning.py
 tests/test_visit_planner.py tests/test_worker_lifecycle.py:55PASS(017),
48PASS(018,bezplanera),68PASS(019),55PASS(020,bezplanera). Są to nakładające się zbiory,
nie sumować. Build/compileall/sh-n/diff-checkPASS. Dwa ostrzeżenia deprecacji narzędzi.
E2E obu silników: generowanie zadania -> wykonanie z jawnym kontaktem -> nowa data ->
indywidualny okres klienta. LokalnyChromiumPASS; lokalnyWebKit nie wystartował przez
brak staregoMiniBrowser, niezależnyWebKit wCI przeszedł. Brak testu nowegoUI na fizycznym
 iPhonie. Wcześniejszy testPWA właściciela nie jest przypisywany nowym funkcjom.

## Schemat, bezpieczeństwo i status

Kod/testy **PASS** na danych syntetycznych. Wydanie/uruchomienie produkcyjne **BLOCKED**.
FOCUS_CALENDAR_SCHEMA_ENABLED=false (opcjonalny native-alembic.ini/006 z004),
FOCUS_CALENDAR_ENABLED=false (runtime). Obie domyślnieOFF. Wyłączenie runtime nie
wymaga downgrade. Profile005/006 nie są automatycznie łączone. Marker rollback006->004
zachowuje tabele/dane; test fingerprintów wykonano lokalnie, bezprodukcji.
ZgodaA pozostaje wyłącznie004/17. Nowa006 wymaga osobnej zgody i manifestu21tabel.
Nie wykonano SQLprodukcji/SSH, migracji, eksportu, restore/PITR, merge/deploy, zmian
Render/sieci/sekretów, aktywacjiGoogle/Meta/DM ani nowych płatnych zasobów. Focus1/2
niezmienione; prywatne ZIP-y zachowano pozaGit. Nie ujawniono sekretów/danych klientów.

## Blokady i następny etap

Aktualna integralność/kontaSQL004/17, RPO≤60min, trwały magazyn/klucz i operacyjny
rollback/handoff pozostają niepotwierdzone. TCPgrant pusty, bez ponawianiaSSH.
Brak webpush, drag&drop, zatwierdzonej retencji nowych metadanych i większych testów
skali/paginacji (taskAPIlimit1000, remindersbatch500). Prace te nie są przedstawiane
jako gotowe. Szacunek nadal≥5 sesji podstawowych +≥1DM, bez redukcji za same funkcje.
Najważniejszy kolejny etap: retencja i pomiar skali/paginacja nowego modułu; przed
jakimkolwiek wydaniem konieczne zamknięcie recovery/SQL oraz osobna zgoda właściciela.

## Dodatkowa poprawka021

Naprawiono dryf02:30->03:30 w cyklu przy wiosennej zmianie czasu. Nieistniejące
wystąpienie pomijane, jesienią wybierane pierwsze; godzina lokalna nie dryfuje.
4nowe testy lokalnePASS/0.46s, bezDB/HTTP. Całość po tej zmianie wymaga końcowegoCI.
Raport021 zapisany. Kolejny etap nadal retencja/skala, bez dalszego rozwoju Google.
