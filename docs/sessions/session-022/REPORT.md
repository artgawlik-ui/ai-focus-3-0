# RAPORT AI FOCUS3.0.4 — SESJA022

## Wejście, zakres i bezpieczeństwo

ffeabe0c1b9412d1117fa45ec3a04ea0be55630f potwierdzone lokalnie/GitHub; CI42307197721
SUCCESS/304, PR3Draft. Odczytano RESUME/raportporanny/021. Nowszych zmian nie nadpisano;
prywatne ZIP-y pozostają pozaGit. Środowisko revision5, TCP puste, 0SSH/SQLprodukcji.
Nie rozwijano/nie usuwano kodu ani danych Google. Nie wykonano merge/deploy/produkcji,
eksportów/restore/PITR, zmianRender/sieci/sekretów, Meta/DM ani nowych płatnych usług.
Focus1.0/2.0 niezmienione. Standardowy schemat004 pozostaje bez zmian.

## Rzeczywiste poprawki

- Kontakty: zbiorcze ustalenie najnowszego rzeczywistego kontaktu, wczesne scopeowner/
  manager i opt-out, normalizacja dat, ignorowanie przyszłych/nieprawidłowych dowodów.
  Usunięto sieciowe N+1 i tysiące wewnętrznych indexprobes po analizieEXPLAIN.
- Strony contacts/tasks/visits/notifications: limit1–100,offset0–100000, pełne total,
  stabilnyID przy remisach, filtry salon/handlowiec/termin/status/priorytet. SQLparametry
  wiązane, bez interpolacji danych użytkownika. Żadnego rozszerzenia dostępu.
- Stare listy JSONarray zachowane, teraz ograniczone i z nagłówkami total/has_more.
  Report ma podglądy20, ale agregaty pełnego zakresu — nie ucinają się na1000zadaniach.
- PWA: paginacja, filtry, wyszukiwanie z opóźnieniem, kontrola nieaktualnych odpowiedzi,
  wyszukiwany selektor klienta (także poza pierwszymi500) i bezpośredni profil klienta.
- Przypomnienia: stare już obsłużone terminy nie blokują kolejnych partii. Do500task+
  500visit/przebieg, ONCONFLICT utrzymuje tożsamość/odczyt. Aktualność liczona przedLIMIT,
  zmiana terminu/opiekuna/statusu nie ujawnia starego wpisu. Feed wyliczany jednorazowo
  z wczesnym filtrem użytkownika; usunięto zły plan dla małych/średnich skrzynek.
- Worker przygotowuje do100follow-up/user/cykl, z ponownym sprawdzeniem pod blokadą
  kontaktu/rekordu. Globalny advisorylock, retry/restart i deduplikacja zachowane.
- Retencja: owner-only preview, wyłącznie liczby i propozycje, bez wykonawcy kasowania.
  Nawet FOCUS_RETENTION_ENABLED=true nie aktywuje DML. Klienci, kontakty i wizyty nigdy
  nie są kandydatami. Zadania oceniane od completed_at, nie od daty utworzenia klienta.

Kontrakty i ograniczenia: PAGINATION.md, RETENTION_POLICY.md.
Opcjonalna007 dodaje6indeksów w profilu native; upgrade/repeat/check/down testowane
na syntetycznymPG. Down006 usuwa wyłącznie te indeksy. Fingerprinty zapisanych danych
przed/po zgodne. Nowych tabel nie dodano (nadal21 w profilu native),004/17 bez zmian.
Indeksy rejestruje tylko profil native; nie zmieniają legacy modelu004. Produkcyjna
migracja007 wymaga osobnej zgody i testu kopii; zgodyA nie rozszerzono.

## Pomiary — fakty, nie obietnice sprzętu Render

Pełne próbki/metadata/plany: performance/README.md i measurements.json, EXPLAINANALYZE
każdego rozmiaru. PG17.11, Docker1CPU/512MiB, API Python/TestClient na hoście. Małe
teksty, syntetyczne profile, celowo jednoczesne wizyty do stresu kolejki. Nie jest to
ruch prawdziwych klientów ani fizycznyiPhone. Jedno rozgrzanie+5próbek, mediana ms:

| Salony | Kontakty20 | Zadania20 | Wizyty20 | Powiadomienia20 | Raport |
|---:|---:|---:|---:|---:|---:|
|300|9.917|7.141|8.312|10.996|31.099|
|1000|14.208|7.430|9.621|31.750|50.067|
|5000|39.001|13.431|16.342|53.573|173.006|
|10000|80.369|23.597|27.254|101.467|320.594|

Powiadomienia to faktycznie wypełniona skrzynka handlowca120/400/2000/4000, pozostałe
listy managera całego zbioru. Wszystkie300/1000/5000/10000 unikalnych salonów przeszły
przez3/10/50/100stron po100 bez braków/duplikatów. Przy10000 całe przejście11549.028ms.
Generowanie600/2000/10000/20000przypomnień odpowiednio25.421/84.081/769.199/2566.500ms;
końcowa partia0, brak ponownego odnotowania tej samej operacji. Czasy bez minutowych
przerw harmonogramu; nie są SLA dostarczenia ani czasem pełnego planowania10tys.

Porównania prób zachowane: pre-aggregate,pre-feed-role,pre-notification-materialization.
Pierwsza wersja odczytu miała LATERAL/indexprobes; po zmianie na agregację zbiorczą
ponowiono pomiar. Pustą skrzynkę managera zastąpiono aktorem z danymi. Potem plan
UNION powodował przy1000medianę1111.497ms; scopedMATERIALIZED dało31.750ms. Pokazujemy
również wyniki wolniejsze, nie przypisujemy zysku samym indeksom. Dla szerokich list
SeqScan/HashJoin jest prawidłowym wyborem. Stara funkcja pełnej listy miała1501–50001SQL;
jej referencji nie porównujemy do pojedynczej nowej strony jako identycznej operacji.

## Testy i dowody

Nowy tests/test_native_pagination.py: **27 przypadków**. Poprzednie304 zachowane.
- `pytest -q tests/test_native_pagination.py tests/test_native_planning.py
 tests/test_worker_lifecycle.py tests/test_visit_planner.py`: **98PASS/0FAIL/0SKIP,
 52.75s**; po wzmocnieniu testu migracji na3salonach/powiązaniach retencja+migracje3PASS.
  Zestawy nakładają się, nie sumować. Dwa znane ostrzeżenia deprecacji zewnętrznych narzędzi.
- Testy: scope/bounds/searchliteral, stabilne strony305, pełny raport1105, kolejne partie
  2410przypomnień, dwie instancje workera i równoległe generowanie, zachowanie read/at,
  aktualizacja/anulowanie i zmiana właściciela, DST i strefa telefonu, preview bezDML,
  indeksyup/repeat/check/down. Istniejący rzeczywistySIGKILL test nadal przechodzi.
- BuildTS/Vite/compileall/diff-checkPASS. Brak nowych zależności.
- Lokalny Chromium: pełny nowy flowPASS, wyszukiwanie456.03ms, następna strona167.20ms,
  45rekordów/strony20. To pojedyncza próba lokalna, nie wynik fizycznegoiPhone aniSLA.
  CI musi wykonać oba silniki, w tym tapWebKit, i zapisać własne pomiary.
  Opcja lokalnegoChromium jest ignorowana wCI — nie pomijaWebKit w wymaganym workflow.
- Pierwsze błędy nowych testów dotyczyły kodowaniaA+ wURL, logowania po fingerprintach
  i porównania wszystkich ix_focus zamiast6nowych. Poprawiono fixture, nie osłabionoACL.
- PełnyCI dokładnego końcowegoSHA wymagany przedPASS; dowód wChecksPR3 i raporcie
  porannym/komunikacie końcowym. Nie przypisywać nowemuSHA wejściowych304PASS.

## Status i dalszy etap

Kod lokalnie ukończony, produkcyjne wydanie **BLOCKED**. Retencja toDRYRUN/OFF, bez
usuwania. Brak push/realDM/Google. Nie gwarantujemy snapshotu pomiędzy stronami podczas
równoległej zmiany sortowanych pól — odświeżyć pierwszą stronę. Pomiary małych tekstów,
nie bardzo dużych notatek; brak testu fizycznegoiPhone i produkcyjnego sprzętu.
RPO60, aktualna integralność/kontaSQL004, magazyn-klucz, rollback/handoff nadal otwarte.
Szacunek nadal≥5sesji podstawowych +≥1DM, bez mechanicznej redukcji za development.
Następny bezpieczny etap: prywatna diagnostyka kolejki i podgląd retencji w panelu
managera, bez uruchamiania wykonawcy. Operator nadal potrzebuje osobnych zgód przed
wydaniem/migracją/retencją; ta sesja nie wykonuje żadnej z nich.
