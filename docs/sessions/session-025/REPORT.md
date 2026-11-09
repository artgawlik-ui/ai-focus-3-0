# RAPORT AI FOCUS3.0.4 — SESJA025

## Wejście i rzeczywista luka

Kontynuacja po pełnym zielonym CI024:180d7767b60e7b19c7952a72b76adc824bf71586,
workflow PR42653906423 i push42653874111 SUCCESS,364 PASS; build/oba silniki/audyty PASS,
0 znanych podatności. Nie rozpoczęto025 przed spełnieniem tej bramki.

Wykryto w scripts/bootstrap.py: pozostawiony VERIFICATION_PASSWORD mógł tworzyć
technicznego managera przy kolejnym starcie, jeśli użytkownik nie istniał. WORKER_PAUSED
nie obejmuje bootstrapu. To zagrożenie przyszłego wydania, nie dowód aktualnego stanu
konta produkcyjnego. Nie odczytywano wartości żadnych sekretów.

## Zrealizowane zabezpieczenia

- Usunięto automatyczne tworzenie technicznych kont. VERIFICATION_PASSWORD jest teraz
  ignorowany przez bootstrap. Nie dodano flagi umożliwiającej jego ponowną aktywację.
  Testowe konta pozostają wyłącznie jawnie tworzonymi fixture'ami testów.
- Jeśli baza ma użytkowników, bootstrap nie zmienia kont, haseł, ról ani sesji i nie
  potrzebuje starych danych inicjalizujących do ponownego startu. Nie reaktywuje konta.
- Tylko pusta baza: jeden manager inicjalny, hash Argon2id; hasło zgodne z istniejącą
  polityką PasswordIn (12–200 znaków, odrzucenie trywialnych fraz). Limit email254 jak API/DB.
  Zapobiega to m.in. ustawieniu hasła, którego login odrzuciłby z powodu długości.
- Konkurencyjny bootstrap PG: transakcja READ COMMITTED, advisory xact lock z limitem5s,
  ponowny count po uzyskaniu locka. Dwa procesy nie tworzą dwóch managerów. Zweryfikowano
  także przy domyślnej izolacji połączenia REPEATABLE READ, aby uniknąć starego snapshotu.
  Nie zmieniono globalnej konfiguracji bazy. SQLite nie otrzymał obietnicy tej współbieżności.
- Błędy walidacji i sterownika kończą CLI bez powodzenia, ale z ogólnym komunikatem,
  bez wejściowych wartości/tracebacku Pydantic i szczegółów SQL. Nie ukrywa się błędu
  jako sukcesu ani nie podejmuje automatycznego recovery lub zmiany uprawnień.

Nie uruchamiano bootstrapu na produkcji. Istniejące konta techniczne nie zostały usunięte,
wyłączone ani odblokowane; ich sesji nie unieważniono. Aktualny stan nadal wymaga A.
Kod d15265b nie otrzymuje tej poprawki przy rollbacku; jego snapshot start/env pozostaje bramką.

## Testy

16 nowych przypadków w tests/test_bootstrap_safety.py, wyłącznie syntetyczny PostgreSQL.
- stale/missing/short legacy sekret bez odtworzenia użytkownika;
- istniejące konta i dodatnia próbka sesji bez zmian fingerprintów;
- wyłączony techniczny użytkownik pozostaje wyłączony;
- pusta baza: jeden początkowy manager, Argon2id, idempotencja;
- brakujące/krótkie/trywialne/za długie hasło i za długi email bez utworzenia kont;
- awaria przed commit bez częściowego konta i bez prywatnych detali w stderr/trace;
- dwa konkurencyjne starty, oba kończą poprawnie, tylko jeden hash/konto (RC oraz RR).

`pytest -q tests/test_bootstrap_safety.py tests/test_api.py
 tests/test_release_native_rehearsal.py tests/test_runtime_packaging.py
 tests/test_release_rehearsal.py tests/test_worker_lifecycle.py`:
**56 PASS/0FAIL/0SKIP,56.69s**. Po wzmocnieniu dodatnią próbką istniejącej sesji:
`pytest -q tests/test_bootstrap_safety.py`: **16 PASS/0FAIL/0SKIP,6.55s**.
Zbiory nakładają się, nie sumować. Dwa znane ostrzeżenia AnyIO/Starlette.

Przy pierwszej wersji fixture wyścigu próbowano podmienić read-only metodę obiektu
PasswordHasher:2FAIL/54PASS. Podmieniono zależność modułu na kontrolowany wrapper,
pozostawiając prawdziwy Argon2 do hashowania. Po korekcie56 PASS; nie osłabiono testu,
nie zwiększono istniejących timeoutów i nie wprowadzono pominięć.

Pełny końcowy CI nowego SHA ma potwierdzić380 testów, build, Chromium/WebKit i oba audyty.
Do tego momentu025 IN PROGRESS, a produkcja BLOCKED. Nie dziedziczyć364 PASS z024.
Nie uruchamiano ręcznie ponownie niezmienionych browser tests; pełny CI sprawdzi całość.

## Wydanie, granice i dalszy krok

Aktualizacja macierzy: docs/reports/PRODUCTION_READINESS.md. Zmienił się wyłącznie kod
bootstrapu, testy i dokumentacja. Brak nowej migracji, zależności, flag, procesów i kosztów.
Reguły biznesowe CRM/agenta, opt-out, kontaktów i kalendarza zachowane. Google bez zmian.
Nie zmieniono żadnych kont/sekretów/Render/sieci/uprawnień produkcyjnych;0 SSH/SQL.
Bez merge/deploy/production migrations/cleanup/export/restore/PITR i Meta/DM.
Focus1.0/2.0 nietknięte, PR3Draft, prywatne archiwa zachowane.

Nie usuwać dziś VERIFICATION_PASSWORD w panelu: to zmiana konfiguracji wymagająca zgody;
rollback może użyć starego snapshotu env. Przed wydaniem nadal: aktualne004/17 i konta,
RPO≤60min, trwały magazyn i klucz, artefakt/env rollbacku, handoff oraz osobna zgoda.
Nie da się zamknąć tych bramek kolejnym testem na danych syntetycznych.

Szacunek bez zmian ≥5 sesji podstawowych +≥1 DM. Najważniejsza następna czynność:
udostępnienie zatwierdzonego wewnętrznego kanału READ ONLY do dokładnie4SELECT-ów005,
a potem prywatne potwierdzenie kont. Zgoda A udzielona; nie prosimy o nią ponownie.

Pliki: scripts/bootstrap.py, tests/test_bootstrap_safety.py, dokumenty025,
aktualizacja dowodów024/PRODUCTION_READINESS/RESUME/raportu porannego.
