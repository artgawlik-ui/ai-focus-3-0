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

# Wznowienie po sesji022

Wejścieffeabe0/CI42307197721 SUCCESS/304 potwierdzone, PR3Draft. Nowe: paginacja
contacts/tasks/visits/notifications, filtry, pełne agregaty bez limitu1000, zbiorczy
monitoring i sprawiedliwe partie przypomnień (do500+500). Źródło feedMATERIALIZED
z wczesnym scope. PWA i selektory klientów stronicowane.27nowych testów, lokalnie98PASS.
Pomiary300/1000/5000/10000 iEXPLAIN zapisane wdocs/sessions/session-022/performance.
Retencja wyłączniepreview, bez kasowania nawet przyflagtrue. Nowa007 tylko indeksy
w opcjonalnym profilu native, dane/tabele zachowane; bez migracji produkcyjnej.
Raport022 i raportporanny zapisane. KońcowyCI tegoHEAD sprawdzić przedPASS.
Następny etap: diagnostyka kolejki i panelpreviewretencji managera. Nie wracać doGoogle.
WydanieBLOCKED: SQL004/17,RPO60,magazyn-klucz,rollback/handoff. A nie rozszerzona.
PR3Draft, bez merge/deploy/produkcji/Meta/DM/kosztów. ≥5podstawowych+≥1DM. ZIP-y zachować.

---

# Końcowy punkt wznowienia sesji021

800c1721b9a079cbc60b6b22f81248fff5f6e199: CI42306632204 SUCCESS/304PASS,
Chromium/WebKit/build/audytyPASS,0 znanych podatności. Łącznie45 nowych przypadków.
Końcowy dopisek zawiera raporty i korektę czasu fixture dnia0 (bez przyszłego12:00);
CI tegoSHA również potwierdzić wChecksPR3. Sesje017–021 ukończone na syntetycznych danych.
Raport zbiorczy: docs/reports/MORNING_PROGRESS_REPORT.md. Następny etap: retencja,
skala/paginacja natywnego modułu, bez powrotu do Google. Nie powtarzać zamkniętych
testów bez nowej zmiany. Feature/schema domyślnieOFF, opcjonalny006 bez migracji produkcji.
WydanieBLOCKED: aktualnySQL004/17, RPO60, magazyn-klucz, rollback/handoff. A aktualna,
nie rozszerzona. PR3Draft; bez merge/deploy/realGoogle/Meta/DM/kosztów. ≥5+≥1DM.
Zachować prywatneZIP-y; nie deklarować pracy w tle po zakończeniu wykonania.

---

# Wznowienie po poprawce021

Po zielonym020 wykryto i naprawiono dryf czasu w cyklu przy DST. Generator pomija
nieistniejące wystąpienie i jesienią wybiera pierwsze, zachowując godzinę lokalną.
4nowe testyPASS/0.46s; łącznie45 nowych od015. PełnyCI tegoSHA sprawdzić przedPASS.
Raport021 i raport poranny zapisane. NadalBLOCKEDprodukcyjne SQL004/RPO60/magazyn-klucz/
rollback-handoff. Bez merge/deploy/Meta/Google/DM/kosztów. PR3Draft, flagiOFF.
Następne zadanie: retencja i skala/paginacja natywnego modułu. ≥5podstawowych+≥1DM.

---

# Potwierdzony punkt wznowienia natywnego Focus

Kod0207afb5bffaa11f4549f7f7a1d695b38bc38d36493: CI42305590784 SUCCESS/300PASS,
Chromium/WebKit/build/audytyPASS,0 znanych podatności. Łącznie41 nowych przypadków.
Dopisek dokumentacyjny ma osobny SHA: jego końcowyCI potwierdzić wChecksPR3.
Raport poranny zawiera zbiorcze dowody i ograniczenia: docs/reports/MORNING_PROGRESS_REPORT.md.
017–020 ukończone na syntetycznych danych; produkcyjne wydanie nadalBLOCKED.
Następny etap: retencja, skala i paginacja natywnego modułu. Google rozwój zakończony.
Nie powtarzać zakończonych testów bez nowej zmiany. Nie aktywować flag/migracji/Meta/DM.
ZgodaA nie rozszerzona; SQL004/17 iRPO60 pozostają otwarte. PR3Draft, ≥5podstawowych+≥1DM.
Brak działania w tle po zakończeniu wykonania. Dalsze szczegóły poniżej.

---

# Wznowienie po sesji020

019cb01fd8 CI42304747622 SUCCESS/297PASS (Chromium/WebKit/audytyPASS).
020: szczegółowy audyt deadline/status/owner/revision i realnySIGKILL procesu przedcommit,
bez częściowych zapisów/duplikacji po restarcie. Lokalnie55PASS; pełnyCI tegoHEAD
sprawdzić przedPASS. Łącznie41 nowych testów od015. Raport020 i raport poranny zapisane.
Google rozwój zakończony; kod/dane005 zachowane, brak aktywacji. Nowy moduł natywny
za schema/runtime domyślnieOFF,006 z004. Nie mieszać005/006 ani nie migrować produkcji.
Następne zadanie: retencja/skala/paginacja nowego modułu. ProdukcyjneSQL004/17, RPO60,
magazyn-klucz i rollback/handoff wciążBLOCKED; zgodaA aktualna, nie rozszerzona.
PR3Draft, bez merge/deploy/Meta/DM/realGoogle/kosztów. ≥5 podstawowych +≥1DM.
Zachować prywatneZIP-y. Nie deklarować pracy w tle po zakończeniu wykonania.

---

# Wznowienie po sesji019 — kalendarz Focus i monitoring

Google wycofany decyzją właściciela; nie rozwijać OAuth/sync ani nie usuwać jego danych.
017ad348f0 CI42302108082 SUCCESS/284;0188c64fa0 CI42303042647 SUCCESS/293.
019raport dnia/2h/24h, filtr managera, jawne reguły ryzyka i indywidualny okres każdego
klienta. Lokalnie68PASS/buildPASS. Końcowy CI bieżącego HEAD sprawdzić przed PASS.
Raport poranny: docs/reports/MORNING_PROGRESS_REPORT.md; raporty017–019 zawierają dowody.
Natywny moduł za dwoma flagami domyślnieOFF: FOCUS_CALENDAR_SCHEMA_ENABLED wybiera
profil006 z004, FOCUS_CALENDAR_ENABLED wyłącznie funkcje/worker. FeatureOFF nie wymaga
downgrade.005 i006 to osobne profile: nie łączyć ich bez zatwierdzonego planu.
Rzeczywisty kontakt tylko Activity call/visit/email_received/instagram_received; brak
kontaktuNULL. Plan, szkic i task nie resetują licznika. ContactPolicy per salon i ustawienia
per priorytet; zadania i przypomnienia deduplikowane. DatyWarszawa/DST, salonlock i RBAC.
Następny etap: retencja/skala/restart natywnego workera; nie wracać do Google.
Nadal BLOCKED: aktualny SQL004/17, RPO60, magazyn-klucz, rollback/handoff. A aktualna
i nie rozszerzona na006. PR3 Draft; bez merge/deploy/produkcji/eksportu/restore/Meta/DM/kosztów.
Brak nowych grantówTCP; nie ponawiać SSH. Zachować prywatne ZIP-y. ≥5 podstawowych+≥1DM.

---

# Wznowienie po sesji018

017 ad348f0 CI42302108082 SUCCESS/284PASS. 018: osobna flaga schematu
FOCUS_CALENDAR_SCHEMA_ENABLED=false + runtimeFOCUS_CALENDAR_ENABLED=false.
Schema006 może zostać aktywny przy runtimeOFF bez blokowania startu aplikacji.
Nie obowiązuje historyczny wybór profilu flagą funkcji z017. Bez produkcyjnej migracji.
Nowe datetime-localWarszawa+fold/DST, settingsGET, pojedyncze aktualne przypomnienia
i blokada salonu przeciw opt-out. Lokalnie48PASS; pełny CI bieżącego HEAD sprawdzić.
Raport018 i raport poranny zapisane. Google rozwój zakończony; nic nie aktywować.
Następne zadanie: pełny raport dnia i zbliżających się wizyt. Produkcyjny gate nadal
BLOCKED (SQL004/17, RPO60, magazyn-klucz, rollback/handoff), ≥5 podstawowych +≥1DM.
PR3 Draft, bez merge/deploy/kosztów/realDM/zmian produkcji. ZIP-y prywatne zachować.

---

# Wznowienie po zmianie priorytetu — sesja017

Właściciel wycofał Google Calendar. Nie rozwijać OAuth/sync. Kod/dane005 zachowane,
panel i linki kalendarza Google wycofane. Sesja016: raport stanu, brak live/testów naprawy.
Natywny moduł: backend/native_planning.py, NativeBase, FocusWorkPanel; flagfalse domyślnie.
Opcjonalny native-alembic.ini ->006 z004, bez zależności005. Nie łączyć profili ani
nie wykonywać downgrade na produkcji. Standardowy004 nie zmieniony.
Kontakt = Activity call/visit/email_received/instagram_received. Brak kontaktu toNULL,
nie data dodania; zadania/szkice/wizyty planowane nie resetują licznika. Cadence per salon
oraz per priorytet. Zadania, wyniki, przypomnienia i raporty mają RBAC i opt-out.
Raport: docs/sessions/session-017/REPORT.md. Raport poranny: docs/reports/MORNING_PROGRESS_REPORT.md.
Końcowy CI tego HEAD sprawdzić przed PASS; nie kopiować 259 z wejściowego c754a36.
Prywatne nieśledzone ZIP-y zachować. PR3 Draft, bez merge/deploy/produkcji/Meta/DM/kosztów.
Nadal BLOCKED: SQL004/17, RPO60, magazyn/klucz, rollback/handoff. A nie rozszerzona na006.
Następny development: ergonomia dat Warszawa i pełniejsze raporty dnia; webpush/dragdrop
niezaimplementowane. Szacunek nadal≥5 podstawowych +≥1DM. Brak podstaw do redukcji.

---

# Wznowienie po sesji 015

[Raport 015](docs/sessions/session-015/REPORT.md),
[Google Calendar](docs/integrations/GOOGLE_CALENDAR_PLAN.md).
Punkt wejściowy 516cd335, CI success/225 potwierdzone przy rozpoczęciu; PR #3 Draft.
Zaimplementowany OAuth sesja/state/PKCE, oddzielny grant użytkownika, Fernet, dedykowany
kalendarz i jawnie zatwierdzana synchronizacja wersji wizyty (kolejka, ETag, retry, cancel).
Panel mobilny + mock transport Google w E2E Chromium/WebKit. Brak realnego Google OAuth/API.
GOOGLE_SCHEMA_ENABLED / GOOGLE_CALENDAR_ENABLED / GOOGLE_CALENDAR_WRITE_ENABLED domyślnie false.
Nie zmieniać produkcyjnych flag. Standardowy Alembic pozostaje 004/17 tabel;
opcjonalne google-alembic.ini ->005/21. Rollback 005->004 tylko marker, zachowuje dane.
Po 005 schema flag musi zostać true do zatwierdzonego downgrade; standardowy profil nie zna005.
Lokalnie 68/68 testów regresji PASS, build/compile/sh/diff PASS. Nowych przypadków 34
(32 Google, 1 lifecycle, 1 fixture). Implementacja778477c: CI42132281549 SUCCESS,
259 passed, Chromium/WebKit PASS, pip/npm0 podatności. Końcowy CI commita dopisku
dokumentacyjnego sprawdzić w PR; nie przypisywać mu automatycznie wyniku implementacji. SHA raportu: git log -1 --format=%H --
docs/sessions/session-015/REPORT.md. Jeśli CI niegreen, najpierw napraw konkretny błąd.
Brak nowego kanału/settera TCP, revision5; bez kolejnych prób SSH i bez produkcyjnego SQL.
Zgoda A aktualna tylko 4 SELECT-y 004/17; przyszłe005 wymaga nowego zatwierdzonego manifestu.
Wydanie BLOCKED: aktualna integralność/konta SQL, RPO60, magazyn/klucz, rollback artefakt/env,
produkcyjny handoff; Google dodatkowo klient Web/test OAuth S256 i zgody na aktywację.
Nie wykonać merge/deploy/migracji/eksportu/restore/PITR/Meta/DM bez osobnej zgody.
Szacunek nadal 5 sesji podstawowych + co najmniej 1 DM. Focus1/2 nietknięte.
Następny bezpieczny krok: zweryfikować pełny CI i przygotować test rejestracji Web OAuth
na zatwierdzonym koncie testowym; operacyjnie potrzebny ograniczony grant TCP Codex
ssh.frankfurt.render.com:22, bez zmiany allowlisty PostgreSQL.

---

# Wznowienie po sesji 014

[Raport 014](docs/sessions/session-014/REPORT.md). Punkt wejściowy 9138215/CI 42094884611
success potwierdzone, PR #3 Draft. Wydanie nadal BLOCKED.
Nowe: istniejące appointments rozszerzone o 1/7 dni i handlowca, edycję daty/minut/notatek,
revision przeciw nadpisaniu, odwołanie, audyt. UI domyślnie propozycja 20 min;
w nowym workflow manager potwierdza po jawnym uzgodnieniu klienta.
VISIT_PLANNER_ENABLED=false domyślnie. Brak zmiany schematu (004), kosztów i produkcji.
Adres do nawigacji musi być ręcznie potwierdzony dla aktualnego profilu; zmiana profilu
unieważnia weryfikację. Ten guard działa również przy panelu OFF. Trasy nie mieszają handlowców.
Google Calendar nadal ręczny link + preview bez zewnętrznych zapisów, OAuth/sync niezaimplementowane.
Projekt: docs/integrations/GOOGLE_CALENDAR_PLAN.md; prawdziwe konto wymaga przyszłej autoryzacji.
16 nowych testów; lokalnie 34/34 regresji oraz końcowy plik 16/16 (zbiory nakładają się),
build/compile/check PASS. Nowy flow mobilny w istniejącym E2E — końcowy CI dokładnego HEAD
sprawdzić w PR, nie przepisywać wyniku wejściowego. Uchwyty przerwanych procesów nie były dowodem.
Pierwszy CI 2b8e16e: backend/build PASS, E2E wymagało jednoznacznej etykiety statusu.
Dodano ARIA Status wizyty i filtrów; konieczne końcowe CI poprawionego SHA.
Brak nowego kanału/grantu/settera, środowisko revision 5. Nie ponawiano TCP/SSH; 0 produkcyjnych SQL.
A aktualna. Nadal SQL/integralność/RPO60/magazyn-klucz/artefakt-env/handoff otwarte.
Najbliższy krok operacyjny: grant TCP Codex ssh.frankfurt.render.com:22, bez zmiany allowlisty;
potem host key/kanał/prywatne ID i 4 SELECT-y. Nie wdrażać ani aktywować integracji bez zgody.
Szacunek nadal 5 sesji podstawowych + ≥1 DM. Kod i dane Focus 1.0/2.0 niezmienione.

---

# Wznowienie po sesji 013

[Raport 013](docs/sessions/session-013/REPORT.md), [macierz dowodów](docs/sessions/session-013/EVIDENCE_GATE.md).
Punkt wejściowy a276463 / CI 42090550994 success, PR #3 Draft. Wydanie BLOCKED.
Nowa funkcja: miejscowość + jawne centrum + promień 1–50 km, dystans/źródło/data OSM,
formularz weryfikacji przed zapisem. DISCOVERY_RADIUS_ENABLED=false domyślnie;
GEOCODING_SEARCH_URL konfigurowalny HTTPS. Stare city-only zachowane.
Bez nowych migracji/zależności/produkcji. Geokoder ma publiczny cache/rate limit także
między procesami PG. Nie wysyła CRM; nie ma autocomplete ani realnych testów dostawcy.
23 nowe testy (19 funkcji +4 bezpieczeństwa fixture), lokalna regresja 56/56 +4/4, build PASS.
Pierwszy CI cb64017: backend 205 PASS, Chromium PASS, WebKit nie otrzymał testowej flagi.
Korekta E2E: flaga w izolowanym serwerze, transport HTTP dostawcy fixture ze ścisłym guardem;
przeglądarki używają rzeczywistego API. Koniecznie sprawdzić CI poprawionego HEAD. Nowy UI w Chromium/WebKit na fixture
w istniejącym CI; końcowy wynik exact HEAD w Checks PR #3, nie przepisywać starszego PASS.
README poprawione: start.sh już startuje worker; status produkcji jest datowany.
TCP sprawdzone raz, puste. Brak narzędzia ustawienia reguły; 0 SSH/SELECT, A aktualna.
Nadal SQL/integralność/RPO60/magazyn i klucz/artefakt-env/handoff są otwarte.
Najbliższy krok: aktywacja jednego grantu TCP Codex ssh.frankfurt.render.com:22,
potem zaufany host/kanał/prywatne ID i tylko 4 SELECT-y. Bez zmian allowlisty.
Nie aktywować Meta lub wyszukiwania promienia na produkcji bez zgody. Bez merge/deploy.
Szacunek 5 sesji podstawowych + ≥1 DM nie maleje bez zamknięcia rzeczywistych wymagań.

---

# Wznowienie po sesji 012

[Raport 012](docs/sessions/session-012/REPORT.md). Wydanie nadal BLOCKED.
Punkt wejściowy c538b9a / CI 42085434097 success potwierdzone; PR #3 Draft.
Nowe: próba rzeczywistych procesów starego d15265b i nowego workera na syntetycznym PG17,
pause/SIGTERM/kill/resume, pojedynczy szkic, stare API health/401 i 17 hashów bez zmian.
API teraz odrzuca Job dla trwałego Meta opt-out, pod wspólną blokadą kontaktu.
4 nowe testy; lokalna regresja 59/59 PASS, rozszerzona po CI: 69/69 PASS.
CI 9c15a57 wykazało 185 PASS/1 FAIL (nieaktualne założenie testu opt-out).
Test wzmocniono: 409 dla nowego Job oraz odrzucenie starego zadania po rezygnacji.
Nie pomijać końcowego CI nowego HEAD; wynik w Checks PR #3. CI potrzebuje historii Git do starego kodu:
checkout fetch-depth=0; nie włącza to merge/deploy ani operacji Render.
Testy rollbacku nie uruchamiają starego workera po cofnięciu: nie jest to pełny rollback
Render. Stary worker nie zna pauzy/fencing/Meta opt-out — przed takim cofnięciem STOP
przy niepotwierdzonej kontroli kolejki/retencji i procesów. Nie omijać tego WORKER_PAUSED.
Render GET: d15265b nadal live; brak eligibility artefaktu i env snapshot w get_deploy.
Brak nowego dowodu latest recovery point, RPO60 nadal niepotwierdzone; nie tworzono kopii.
TCP nadal puste; 0 SSH/SELECT. A aktualna, grant i prywatne ID niepotwierdzone.
Najbliższa czynność: grant TCP Codex do ssh.frankfurt.render.com:22, bez zmiany allowlisty.
Nadal wymagane aktualne SQL/konta/hash, recovery/RPO/klucz/magazyn, artefakt/env i handoff.
Szacunek 5 sesji podstawowych + ≥1 DM nie maleje bez zamknięcia tych wymagań.
Końcowe CI HEAD sprawdzić w Checks PR #3; wyniku wejściowego nie przepisywać na nowy SHA.
Brak deploy/merge/produkcyjnych zmian/Meta/realnych DM. Dalszy punkt: REPORT.md 012.

---

# Wznowienie po sesji 011

[Raport 011](docs/sessions/session-011/REPORT.md), [plan rollout/drain](docs/sessions/session-011/ROLLOUT.md).
Status wydania **BLOCKED**. Punkt wejściowy 64b1719 i CI 42081843358 success potwierdzone.
Nowy kod: fencing przejęcia Job przed zapisem wyniku/błędu; pauza całego workera
WORKER_PAUSED (domyślnie false, błędna/pusta wartość pauzuje) lub lokalny pause file;
SIGTERM nie zaczyna kolejnego etapu, plik statusu operacyjnego bez PII.
Brak zmiany schematu/flag Meta/płatnego AI; nie uruchomiono pauzy ani rollout na produkcji.
Nowe testy 011: 14; lokalny PG17 regresja 94/94, ponowny worker lifecycle 13/13,
supervisor 6/6. Zbiory częściowo nakładają się; końcowy CI sprawdzić dla HEAD PR #3.
Pierwszy deploy musi startować z nowym workerem w pauzie, Meta OFF; dopiero po
potwierdzeniu zakończenia starych procesów osobna zgoda na wznowienie. Stary kod
nie przestrzega nowych zabezpieczeń; rollback je usuwa i wymaga drain przed cofnięciem.
API health sprawdza bazę, nie worker. Status ulotny nie jest zewnętrznym monitoringiem.
TCP grant nadal pusty, zero SSH/SQL. Zgoda A aktualna, prywatne ID niepotwierdzone.
Render GET: PG17 available, 0.1c-256mb, 1GB; brak latest point w dostępnych metadata.
RPO60, aktualna integralność/konta, magazyn/klucz i artefakt/env rollbacku nadal otwarte.
Najbliższy krok właściciela: grant TCP Codex do ssh.frankfurt.render.com:22;
nie otwierać allowlisty. Brak zgody na merge/deploy/eksport/PITR/konfigurację/Meta/DM.
Pozostaje szacunkowo 5 sesji podstawowych + ≥1 DM; termin zależy od dowodów recovery/dostępu.

---

# Wznowienie po sesji 010

[Raport 010](docs/sessions/session-010/REPORT.md). Wydanie nadal BLOCKED.
Sesja 009 zapisana i wysłana: 9858db3177dd003e9463d55ec72eb8fd406287bb.
Sesja 010 dodaje wspólną transakcyjną blokadę kontaktu salonu (PostgreSQL advisory)
w workerze, zapisie opt-out i wiązaniu rozmowy. Bez migracji i zmian flag.
Lokalny PG17: 36 testów PASS, w tym 3 nowe testy integracji/współbieżności;
rozszerzona regresja Meta/inbox/worker/supervisor: 85/85 PASS (zbiory nakładają się).
CI 009 zakończone success: https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42081039659.
Kod 010 wysłany jako def70f3; opis PR przez REST zaktualizowany, Draft potwierdzony.
Wynik CI końcowego SHA sprawdzić w Checks PR #3; nie deklarować PASS przed success.
Przy rolling deploy stare procesy nie przestrzegają nowej blokady: wymagane zakończenie
starych workerów przed aktywacją odbioru Meta. Transport DM pozostaje wyłączony.
Brak grantu SSH/aktualnego SQL, dowodu RPO60 i weryfikacji artefaktu rollbacku nadal blokuje wydanie.
Zgoda A aktualna. Następny krok: grant TCP Codex do ssh.frankfurt.render.com:22,
potem weryfikacja hosta/kanału i dokładnie 4 SELECT-y. Bez otwierania allowlisty.
Szacunek nadal 5 sesji podstawowych + ≥1 DM; operacyjne bramki niezamknięte.

---

# Aktualizacja po sesji 009

Raport: [sesja 009](docs/sessions/session-009/REPORT.md). Wydanie nadal **BLOCKED**.
Nowe poprawki workera: awaria opcjonalnego AI zachowuje analizę regułową;
ponowna kontrola dostępu i blokady kontaktu przed zapisem szkicu, odświeżenie ORM
oraz blokady użytkownika/salonu do końca transakcji. Bez zmiany flag i schematu.
Lokalnie 29 testów PASS (17 nowych). CI dokładnego HEAD sprawdzić w PR #3.
Punkt wejściowy: 05a9e6be77b6993d942a9b4cc76398527b403298.
Przy wznowieniu jego CI nadal trwało; backend/build miały success, E2E/audyty oczekiwały.
Nie powtarzać testów bez przyczyny. Zgoda A pozostaje aktualna, TCP nadal puste.
RPO 60 niepotwierdzone. Bez produkcyjnego SQL, deployu, merge i aktywacji Meta.
Szacunek nadal 5 sesji podstawowych + ≥1 DM, zależny od zamknięcia bramek.

---

# AI FOCUS 3.0.4 — punkt wznowienia po sesji 008

**Status wydania: BLOCKED.** Raport: [sesja 008](docs/sessions/session-008/REPORT.md).

Właściciel w poleceniu sesji 008 potwierdził **zgodę A** na dokładnie cztery SELECT-y
przez autoryzowany wewnętrzny kanał READ ONLY oraz **kontrolowany tryb workera**.
Zapis/push tej gałęzi są zatwierdzone. Wcześniejsze ograniczenie wyłącznie lokalnej
pracy oraz historyczne „A nieudzielona” nie opisują aktualnej decyzji. Nie prosić o A ponownie.
RPO=3600 s pozostaje wymagane i niepotwierdzone.

Checkpoint wejściowy 008: **33790a728493e3a19d97fc455b1f76be6d452ce0**;
PR #3 open/Draft, baza d15265b; CI PR 42062017735 success.
W 008 potwierdzono running/connected/current środowiska, ale polityka TCP nadal ma
`domains=[]`, `ip_ranges=[]`, VPN=false. **Brak grantu SSH; 0 prób SSH, 0 SELECT-ów.**
Jedyna bieżąca czynność odblokowująca dostęp: w konfiguracji środowiska Codex zatwierdzić
ograniczony grant TCP do `ssh.frankfurt.render.com:22`. Nie zmieniać allowlisty PostgreSQL.
Po grancie najpierw zweryfikować host key/autoryzację/kanał; nie zakładać ich dostępności.
Identyfikatory kont wymagają prywatnego potwierdzenia; nie zgadywać ich.

Nowa rzeczywista poprawka 008: supervisor obejmuje start dzieci procedurą zamykania,
aby błąd uruchomienia workera nie zostawiał API bez nadzoru. Pięć nowych testów na mockach;
lokalnie 12/12 PASS łącznie z istniejącymi testami gate i offsite. Bez zmiany flag,
poleceń startowych, schematu, semantyki workera lub limitu zamykania 25 s.
Pełna regresja jest sprawdzana w standardowym CI gałęzi; wynik dokładnego końcowego SHA
odczytać w Checks. Nie przypisywać wyniku checkpointu nowemu commitowi.
Nie powtarzano restore eksportu, nie uruchamiano późniejszych nieudanych prób lokalnego startu.

## Następna sesja — bez powtarzania zamkniętych etapów

1. Sprawdzić HEAD/PR/CI ostatniego commita i stan grantu TCP.
2. Bez grantu nie próbować SSH. Po grancie zweryfikować zaufaną tożsamość hosta i kanał READ ONLY;
   potem dokładnie cztery zatwierdzone SELECT-y z sesji 005, bez DML/DDL i danych osobowych.
3. RPO: nadal brak dowodu latest recoverable point ≤60 min i skuteczności tej ścieżki.
   AVAILABLE i snapshot 17/23/004 nie zamykają tej bramki. Restore/testowa recovery DB,
   nowe kopie/eksporty, koszty i zmiany konfiguracji wymagają osobnej zgody.
4. Potwierdzić dostępność artefaktu/env rollbacku i kontrolę zapisów/retencji workera
   przed osobno zatwierdzonym wydaniem. Kontrolowany tryb zaakceptowano, nie wykonano rollout.
5. Bez merge/deploy/restartu/cleanup/migracji produkcji/aktywacji Meta i realnych DM.

Pozostaje szacunkowo **5 sesji podstawowych + ≥1 dotycząca DM**; licznik nie maleje
za poprawkę kodu i dokumentacji przy otwartych bramkach operacyjnych. Nie jest to termin gwarantowany.
SHA aktualizacji: `git log -1 --format=%H -- RESUME.md`. Raport końcowy rozmowy wskazuje
zweryfikowany SHA i CI. Poniżej zachowano historyczne dowody sesji 001–007.

## Źródło prawdy i zapisany commit

- Repozytorium: https://github.com/artgawlik-ui/ai-focus-3-0
- Gałąź: `fix/3.0.4-meta-validation`.
- Draft PR #3: https://github.com/artgawlik-ui/ai-focus-3-0/pull/3 — open, bez merge.
- Ostatni zweryfikowany commit kodu/dokumentacji przed tym punktem wznowienia:
  **19cf9db71474df0588f74cdaa91839c752ee8602**.
- Lokalny HEAD, zdalna gałąź i PR HEAD były zgodne z tym SHA przed zapisem RESUME.md.
- Pierwotny commit dodający RESUME.md: 60644d8bc208f356060b7629273c1412786d14a2.
  Ostatnia aktualizacja tego pliku (może być późniejsza) ma SHA:
  `git log -1 --format=%H -- RESUME.md`; nie wpisujemy rekurencyjnie własnego przyszłego SHA.
  Końcowy SHA checkpointu podano również w raporcie rozmowy i opisie PR.
- Main/baza PR i ostatnia potwierdzona produkcja: d15265b26524d594bdbcb4bc6b63fcbc398a1424,
  wersja 3.0.3, deploy dep-dbjhl6jbc2fs73crj65g. To datowany odczyt, nie gwarancja stanu
  w nowej sesji. Lokalny ref main bywał starszy — porównywać z aktualną bazą PR/origin/main.

Wszystkie zatwierdzone zmiany kodu i dokumentacji sesji 001–006 są już w zdalnej gałęzi
oraz PR. Żadnych zmian aplikacji/stanu produkcji nie wprowadzono w tym checkpoincie.
Nieśledzone lokalne archiwa reports/ai-focus-3-audit.zip, ai-focus-3-meta-audit.zip,
ai-focus-3-phase-1-2.zip nie są nowymi zmianami kodu/dokumentacji; nie otwierano ich
ani nie publikowano. Mogą zawierać dane prywatne. Nie są wymagane do odtworzenia kodu.
`.render-auth`, klucze, cookies, kopie i dumpy nie są częścią repo. Nie zakładać ich trwałości
ani dostępności po przerwie; używać oficjalnej autoryzacji usług, nigdy sekretów w rozmowie.

## Wyniki CI — przypisane do konkretnego SHA

Dla **19cf9db** ponownie odczytano success obu uruchomień:
- PR: https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41361537654
- push: https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41361532882
- **143 testy PASS**, build frontendu PASS, Chromium desktop PASS,
  WebKit z emulacją iPhone'a PASS; pip-audit/npm audit: 0 znanych podatności.
- 11 testów operatorskiego cleanup celowo wykluczonych z kolekcji, zgodnie z zakazem;
  nie przedstawiać ich jako wykonanych. Regresja krytycznych funkcji aplikacji pozostała.
  Procentowego code coverage nie mierzono. Lista i wyjaśnienie: session-004/FINAL_REVIEW.md.
- Prawdziwą instalację PWA i logowanie na fizycznym iPhonie wcześniej potwierdził właściciel,
  nie Codex. Test WebKit nie jest testem fizycznego urządzenia ani realnego OAuth Meta.

Nowy checkpoint może wywołać oddzielne CI. W nowej sesji odczytać checks jego dokładnego
SHA; nie przepisywać wyniku 19cf9db jako wyniku innego commita. Nie powtarzać lokalnie
niezmienionych pełnych testów/restore bez nowej przyczyny, regresji lub zmiany kodu.

## Obowiązujące decyzje właściciela

1. **RPO = 60 minut / 3600 s**, zatwierdzone 2 listopada. Polityka i gate:
   docs/sessions/session-006/rpo-policy.json oraz docs/meta/3.0.4/RELEASE_GATE.md.
2. Rutynowy kod/testy/dokumentacja wyłącznie na gałęzi roboczej są autoryzowane.
   Nie pytać ponownie o oczywiste kroki w tym zakresie.
3. Historycznie zatwierdzono bazowy koszt Render około 13 USD/mies.; to nie jest zgoda
   na nowy zasób, recovery DB, PITR, nowy magazyn, zmianę planu lub dodatkowe opłaty.
4. Kwota około 0,20 USD compute/24h testowej recovery DB była **wyłącznie propozycją**.
   **Nie zatwierdzono jej utworzenia/testu/usunięcia** ani innych płatnych operacji.
5. Meta działa tylko jako przygotowany kod/mocks; rzeczywista komunikacja wymaga osobnych
   zgód. Każda wiadomość i wizyta wymaga akceptacji. Nie wysyłać testowych DM.
6. Wcześniej zatwierdzono parametry inboxa: done payload 7 dni, metadata 90 dni;
   alert pending ≥100, najstarszy pending >5 min lub dead-letter ≥1;
   przetwarzanie w istniejącym procesie, bez nowego workera/usługi.
   Nie mylić tego z zatwierdzeniem backup retention/nowego magazynu.

## Co zakończono — nie powtarzać bez powodu

- Kod CRM i przygotowanie Meta na aktualnej gałęzi; schema/model zgodne z bazą PR,
  jedyny Alembic head **004**, bez nowych migracji w sesjach 001–006.
- Syntetyczne testy migracji/odtwarzania 17 tabel, sesji i RBAC, CRM, agenta, Meta
  (mocki), inboxa/deduplikacji/lease/retencji/opt-out, szyfrowania i braku DM.
- Bezpieczne preflighty: scripts/readonly_preflight.py, scripts/release_selects.py;
  SQL bez danych/sekretów: docs/sessions/session-005/SELECTS.sql i SELECTS.psql.
  Wariant .sql ma parametry psycopg, .psql prywatne prompt-y psql; nie mieszać formatów.
- **OWNER_VERIFIED:** rzeczywisty eksport z 1 listopada odtworzony lokalnie na PG17.11:
  17 tabel, 23 rekordy, Alembic 004. Samo potwierdzenie nie zawierało SHA/ID pliku.
- **Niezależnie zweryfikowany eksport:** etykieta 2026-11-01 18:25 UTC / 19:25 Warszawa,
  TOC 18:27:29 UTC, 8 996 B, SHA-256
  c7fcd97d374cd3d3696b9ea35a1a99dc83a944e460c890131ad5966d97232a8c.
  Restore do nowego lokalnego kontenera bez sieci/aplikacji/Meta: 17 tabel/23 rekordy/004,
  hash/count i schemat zgodne. Oryginał niezmieniony; kontener/jawne pliki usunięto.
  Nie odtwarzać ponownie tego samego SHA tylko w celu uzyskania kolejnego PASS.
- Reporty sesji 001–006, runbook dostępu, osobne decyzje A/B/C (READ ONLY, cleanup,
  merge/deploy) oraz plan rolling deploy/STOP/recovery. To plany, nie wykonane zgody.

## Aktualne blokady — nie deklarować READY

### A. RPO 60 — niepotwierdzone operacyjnie

Płatny compute PostgreSQL 0.1c-256mb, 1 GB, PG17, Frankfurt; obsługuje PITR.
W sesji 006 API zwracało AVAILABLE i startsAt=2026-10-29T06:32:47Z, bez endsAt/najnowszego punktu/lag WAL. Nowszy odczyt sesji 007 znajduje się na początku tego pliku.
Dokumentacja zabrania punktu z ostatnich 10 min; to nie SLA maksymalnego lag 10 min.
Hobby ma okno 3 dni, Pro+ 7 dni; rzeczywisty workspace billing tier nie jest potwierdzony.
Większa retencja/compute sama nie dowodzi RPO. Nie kupować upgrade jako domyślnego rozwiązania.

Przy odczycie w sesji 006 ostatni eksport miał 17 278 s (4h47m58s), więc sam nie spełniał
60 min. Wiek pobrania/restore nie odświeża punktu źródłowego. Trzeba nowego odczytu,
nie zakładać, że ta liczba lub lista eksportów nadal są aktualne po przerwie.
Brakuje najnowszego skutecznego punktu, testu ścieżki PITR w RPO, nadzoru świeżości
oraz uzgodnionego zakresu awarii (w tym niezależnej ścieżki przy utracie Render).

### B. Dostęp SQL / konta / bieżąca integralność

Hosted Render MCP query jest blokowany przez pustą publiczną allowlistę. Ostatnia polityka
środowiska miała puste granty TCP i VPN=false. Nie otwierać bazy ani nie obchodzić proxy.
Autoryzacja API działała — problemem był kanał SQL, nie konieczność nowego hasła/tokenu.
Potrzebny zatwierdzony wewnętrzny Shell/SSH istniejącej usługi i ograniczony grant wykonawcy,
prywatnie zatwierdzone ID właściciela/technicznego konta. Nie używać historycznych cookies CRM.
Brak świeżego potwierdzenia 004/kont/sesji/hashów. Snapshot 17/23/004 nie jest bieżącą produkcją.

### C. Trwały szyfrowany magazyn i klucz

Nie potwierdzono niezależnego trwałego magazynu/klucza/retencji. OFFSITE_BACKUP_ENABLED było OFF.
Kod offsite jest dzienny, retry po błędzie 1h; backup trzyma SHARE LOCK i dump w RAM.
Samo włączenie lub interwał godzinny nie realizują RPO 60. Proponowana retencja 30 dni
wymaga osobnej akceptacji. Nie uruchamiać nowego eksportu/backup scheduler bez zgody.

### D. Worker / rollout / rollback

AGENT_V2_ENABLED było już ON; **ON/OFF nie zatrzymują workera**. Może zapisywać zadania,
szkice/Activity i wykonywać retencję także przy Meta OFF. Nie wysyła DM ani sam nie tworzy wizyt.
W rolling deploy mogą współistnieć stare/nowe procesy. Wymagane uzgodnione okno bez zapisów
albo rozliczenie każdej zmiany count/SHA, bez pomijania całych tabel w celu wymuszenia PASS.
Ostatni punkt powrotu live: d15265b/dep-dbjhl6jbc2fs73crj65g. API nie potwierdza eligibility
zachowanego obrazu. Przed wydaniem sprawdzić artefakt i env target deployu.
Start.sh uruchamia alembic upgrade head i worker — nie używać go do odczytowego preflightu.

### E. Meta i zgody operacyjne

Zapisana konfiguracja Meta/DM była OFF, env groups 0, paid AI OFF; to datowane metadata,
nie snapshot env działającego procesu ani targetu rollbacku. Nie aktywować integracji.
Development OAuth i Live webhook to oddzielne bramki; dokumentacja wymaga Live do
notifications app users. Nie przełączać trybu i nie wnioskować o Advanced Access bez zgody.
Nie udzielono zgody na merge/deploy/produkcję, cleanup, zmiany sieci/uprawnień/sekretów,
restarty, produkcyjne migracje, nowy eksport, PITR, płatne zasoby i realne DM.

## Sesja 007 — dokładna instrukcja wznowienia

1. Przeczytaj RESUME.md i najnowsze polecenie właściciela oraz aktualny PR #3.
   Sprawdź AGENTS.md, lokalny status, gałąź, HEAD zdalny/PR i checks dokładnego SHA.
   Nie resetuj nowych zmian ani nie nadpisuj pracy innej sesji. Nie myl starego ref main z bazą PR.
2. Przeczytaj aktualne instrukcje środowiska/usług; użyj oficjalnej autoryzacji i sprawdź
   workspace My Workspace. Odczyt Render i metadata był dozwolony; mutacje poniżej nie są.
   Jeżeli nowa sesja nie ma dostępu, zdiagnozuj plugin/CLI przed prośbą o oficjalną autoryzację.
3. W dozwolonym zakresie tylko GET: odśwież recovery/eksporty/plan i policz wiek punktu
   źródłowego względem 3600 s. Spróbuj ustalić latest recoverable point, ale AVAILABLE/startsAt
   nie zastępują dowodu. Nie twórz eksportu, recovery DB ani płatnego testu.
4. Przedstaw najprostszy brakujący krok właściciela: zatwierdzony kanał READ ONLY i/lub
   potwierdzenie latest point przez Recovery/support. Nie wysyłaj wiadomości do supportu samodzielnie.
5. Dopiero po osobnej zgodzie: zaplanowany jednorazowy PITR do izolowanej nowej DB,
   nigdy nadpisanie/zmiana połączeń produkcji. Muszą być zatwierdzone koszt, czas i zakończenie
   testu oraz kanał read-only do nowej DB. Szacunek tej samej 0.1c/256 MB, 1 GB: ok. 0,20 USD
   compute/24h przy 30-dniowym miesiącu, lecz cenę trzeba odczytać ponownie przed zgodą.
6. Bez nowych zgód kontynuuj wyłącznie niezależne lokalne przygotowania/dokumentację,
   nie powtarzaj zakończonych etapów. Nie nazywaj BLOCKED „READY” na podstawie samych testów kodu.
7. Zapisz docs/sessions/session-007/REPORT.md, z rzeczywistymi dowodami i stanem blokad,
   aktualizuj tę samą gałąź/Draft PR bez merge. Testy PostgreSQL tylko sekwencyjnie.

**Stałe ograniczenia:** nie modyfikuj Focus 1.0/2.0, danych klientów, konfiguracji Render/Meta,
sekretów/uprawnień/sieci. Bez DELETE/cleanup, produkcyjnych migracji, restartów, merge/deploy,
nowego eksportu, zakupu zasobów i aktywacji Instagrama bez osobnej zgody. Bez realnych DM.
Nie proś o hasła/tokeny/klucze w czacie; wartości wyłącznie przez zatwierdzony magazyn.
Nie uruchamiaj skryptów z .tools tylko dlatego, że istnieją — część jest historyczna i produkcyjna.

## Najważniejsze pliki

- docs/sessions/session-006/REPORT.md — RPO/plan/źródła/koszty i aktualne kryteria.
- docs/sessions/session-006/RECOVERY_PROCEDURE.md — szyfrowanie/klucze/restore i wariant PITR.
- docs/sessions/session-005/REPORT.md, RELEASE_PLAN.md — snapshot/worker/SELECT/STOP.
- docs/sessions/session-004/FINAL_REVIEW.md — semantyka agenta, wyłączone testy i bezpieczeństwo dowodów.
- docs/sessions/session-003/ACCESS_RUNBOOK.md, DECISIONS.md — dostęp i rozdzielone zgody A/B/C.
- docs/meta/3.0.4/RELEASE_GATE.md — bieżący gate BLOCKED; historyczne READY poniżej nie unieważnia RPO.

Pozostaje szacunkowo **5 sesji podstawowych + co najmniej 1 DM**. Nie zmniejszać licznika
za samo przygotowanie, dopóki krytyczna bramka operacyjna nie zostanie zamknięta.
Ten dokument nie uruchamia pracy w tle, sesji 007 ani GitHub automatyzacji wdrożenia.

## Jedno polecenie dla nowej sesji Codexa

> Wznów sesję 007 Ai Focus 3.0.4 w repozytorium artgawlik-ui/ai-focus-3-0, gałąź fix/3.0.4-meta-validation, PR #3: najpierw przeczytaj RESUME.md z aktualnego HEAD, sprawdź stan gałęzi i CI, a następnie wykonuj plan sesji 007 bez powtarzania zakończonych etapów i z zachowaniem wszystkich zapisanych ograniczeń; RPO=60 minut, status wydania BLOCKED, bez merge/deploy/cleanup/restore/nowego eksportu/zmian produkcji/płatnych zasobów i aktywacji Meta bez nowej osobnej zgody.
