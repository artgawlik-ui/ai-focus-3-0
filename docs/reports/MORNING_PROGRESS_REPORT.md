# Sesja 022 — PASS (kod i testy), 2026-11-09

Commit a11c8aa5dbee197183a719761bb9a06aaba48b50:
https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42639643983 — SUCCESS.
335 testów PASS / 0 FAIL / 0 SKIP, 126.34 s; build, Chromium, WebKit i oba audyty PASS.
0 znanych podatności. Dodatkowe 4 testy naprawy CI (łącznie 31 nowych od wejścia 304).
WebKit w CI: stary limit bitmapy odtworzony; długi dokument pokryty 83 ujęciami,
dashboard 55 ujęciami. Paginacja: 45 rekordów, strony po 20, bez nakładania.
Wyszukiwanie / kolejna strona: Chromium 430.70 / 175.96 ms; WebKit 409.27 / 259.22 ms.
To emulacja iPhone, nie nowy test na fizycznym urządzeniu. Lokalne dowody:
ci-repair-local.json (102 testy regresji, oba silniki, build i audyty).
Równoległy pełny workflow push 42639630411 również zakończył się SUCCESS.
Oba dowody dotyczą dokładnego SHA, nie samego backendu.

Można rozpocząć sesję 023: diagnostyka kolejki i podgląd retencji menedżera.
Produkcja nadal BLOCKED: SQL004/17, RPO≤60 min, magazyn/klucz, rollback i handoff.
PR3 Draft. Bez merge/deploy, migracji produkcyjnych 007, Google/Meta/DM i kosztów.
≥5 sesji podstawowych + ≥1 DM, bez redukcji za sam development.

---

# Sesja022 — naprawa końcowegoCI, 2026-11-09

Workflow42314285868/aa54862FAIL: backend331 i build/ChromiumPASS, WebKit przerwany
limitem bitmapy32767px w pełnym screenshot. Audyty skipped, sesja022 jeszczeINPROGRESS.
Naprawa zachowuje cały dokument jako sekwencję viewportów, bez pomijania testów i bez
wydłużania timeoutów.4nowe testy; wymagany pełnyCI nowegoSHA przedPASS i przed023.
ProdukcjaBLOCKED: SQL004/17,RPO60,magazyn-klucz,rollback/handoff. Bez produkcji/007/
merge/deploy/Google/Meta/DM/kosztów;PR3Draft. ≥5podstawowych+≥1DM.

---

> PierwszeCI022a27c342:331backendPASS, E2EFAIL na wyścigu gotowości selektora.
> Przyciski zapisu zablokowane do gotowości; koniecznyCI poprawionegoSHA.

# Aktualizacja2026-11-07 — sesja022

Paginacja/filtry, zbiorczy monitoring, pełne agregaty i partie przypomnień ukończone
lokalnie. Retencja tylkopreview/OFF, bez wykonawcy.27nowych przypadków, regresja98PASS;
pełnyCI dokładnegoHEAD wymaga potwierdzenia przedPASS. LokalnyChromium nowego flowPASS.
Pomiary orazEXPLAIN dla300/1000/5000/10000: docs/sessions/session-022/performance/README.md.
Mediany kontaktów9.917/14.208/39.001/80.369ms; raportu31.099/50.067/173.006/320.594ms.
Powiadomienia wypełnionego konta10.996/31.750/53.573/101.467ms. PG17.11,1CPU/512MiB,
API na hoście, nie sprzętRender.10tys unikalnych salonów/100stron,20tys przypomnień
bez duplikacji, czas samego generowania2566.5ms. To nieSLA ani fizycznyiPhone.
Indeksy007 opcjonalne, bez nowych tabel. A nadal004/17. Raport022 opisuje próby i ograniczenia.
ProdukcjaBLOCKED(SQL/RPO60/magazyn-klucz/rollback-handoff); PR3Draft. Bez merge/deploy/
produkcji/Google/Meta/DM/kosztów, Focus1/2 nietknięte. ≥5podstawowych+≥1DM bez redukcji.
Następny etap: diagnostyka kolejki i previewretencji w panelu managera.

---

# Raport poranny Ai Focus3.0.4 — 2026-11-06 (Europe/Warsaw)

## Ukończony zakres i punkt wznowienia

Sesje017–021 ukończone i zweryfikowane wCI. Sesja016 została zamknięta po nowej decyzji
właściciela: rezygnacja z dalszej integracji Google Calendar. Nie deklarujemy jej napraw
lub testuGoogle live. Nowy kierunek to natywny Focus, bez kasowania kodu/tabel/danych005.
Ostatni commit aplikacji800c1721b9a079cbc60b6b22f81248fff5f6e199; końcowy dopisek dokumentacyjny
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

**45 nowych przypadków od015:25w017+9w018+4w019+3w020+4w021. PełnyCI:304PASS.**
-017 ad348f0045529a6fa2170b54a69df4f3177d034f — CI42302108082 SUCCESS/284PASS.
-018 8c64fa0ec9189aa95d8e14929f0106f6ede1e649 — CI42303042647 SUCCESS/293PASS.
-019 cb01fd8bb0574362ee1721fa3d061e83dfbe22a4 — CI42304747622 SUCCESS/297PASS.
-021 800c1721b9a079cbc60b6b22f81248fff5f6e199 — CI42306632204 SUCCESS/304PASS:
 https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42306632204.
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
4nowe testy lokalnePASS/0.46s, bezDB/HTTP. PełnyCI304PASS, Chromium/WebKit/audytyPASS.
Raport021 zapisany. Kolejny etap nadal retencja/skala, bez dalszego rozwoju Google.

Końcowy zapis zawiera również korektę fixture dzisiejszego kontaktu (czas aktualny,
nie przyszłe12:00 przy uruchomieniu rano). Brak zmian historii produkcyjnej. Końcowy
SHA zapisu należy potwierdzić wChecksPR3; wyniku aplikacji nie przypisywać automatycznie
commitowi testów/dokumentacji. Raport jest zapisanym punktem wznowienia, nie deklaracją
pracy w tle. Kolejny etap: retencja, skala/paginacja i operacyjne bramki recovery.
