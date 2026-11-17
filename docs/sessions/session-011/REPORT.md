# RAPORT AI FOCUS 3.0.4 — SESJA 011

## DONE — rzeczywiste zmiany

Punkt wejściowy 64b1719c02241da2b7883b7db3bc97429070292a i CI 42081843358 success
odczytane z GitHub. PR #3 Draft. Zachowano nieśledzone prywatne archiwa, bez ich otwierania.
Odczytano RESUME, raport 010, RELEASE_GATE, rollout 005, rollback 004, recovery 006.

1. Fencing Job: przejęcie zapisuje claim timestamp. Przed wynikiem pobierany jest
   wiersz Job FOR UPDATE z warunkami running/updated_at=claim. Po odzyskaniu zadania
   stary wykonawca nie zapisze ani szkicu, ani błędu. Activity i completed nadal są
   jedną transakcją. Nie dodano migracji; schema 004 bez zmian. Możliwa powtórna analiza
   lub wywołanie opcjonalnego modelu po awarii; to nie exactly-once operacji zewnętrznych.
2. Worker main ma sygnał zatrzymania sprawdzany między etapami. SIGTERM kończy bieżący
   etap i nie rozpoczyna kolejnego. Stop nie polega już na zwykłym sleep.
3. WORKER_PAUSED: nieustawione zachowuje działanie; false/0/off/no uruchamia,
   true i inne wartości (w tym pusta) pauzują fail-closed. Lokalny
   /tmp/focus3-worker.pause również pauzuje. W pauzie brak jobów, Meta i retencji.
   Nie jest to zdalny ani rozproszony przełącznik, nie zmieniono ustawień produkcji.
4. Atomowy plik /tmp/focus3-worker-status.json 0600: state/pid/at, bez PII/sekretów.
   Awaria diagnostyki nie zatrzymuje kolejki. API health nie jest health workera.
   Brak wdrożonego zewnętrznego alarmowania — próg >120 s to propozycja operatorska.
5. Rozpisano dwuetapowy pierwszy rollout: nowy worker paused, potwierdzenie końca
   starych procesów, dopiero osobno zatwierdzone wznowienie. Stare wersje nie respektują
   fencing/pauzy/blokady 010. Rollback do d15265b wymaga drain i traci te zabezpieczenia.
   Brak downgrade/overwrite bazy; modele i migracje niezmienione.

## Testy

- Syntetyczny lokalny PostgreSQL 17, 256 MB/1 CPU, loopback 55432; żadnych danych klientów.
- `pytest -q tests/test_worker_lifecycle.py tests/test_agent_resilience.py tests/test_contact_concurrency.py tests/test_api.py tests/test_supervise.py tests/test_meta_303.py tests/test_meta_304.py`:
  **94 passed, 0 failed/skipped, 31.36 s** (przed dodaniem ostatniego testu diagnostyki
  i restartu supervisora).
- Po końcowej poprawce zapisu statusu `pytest -q tests/test_worker_lifecycle.py`:
  **13 passed, 0 failed/skipped, 4.59 s**. Dwie równoległe sesje: stary wykonawca
  zatrzymany na analizie, syntetyczne odzyskanie po 6 min, nowy wykonawca kończy,
  stary wraca lub zgłasza błąd; w obu przypadkach 1 szkic i completed.
- `pytest -q tests/test_supervise.py`: **6 passed**; nowy przypadek ponownego startu
  supervisora po awarii dziecka potwierdza brak zachowania poprzedniego stanu.
- **14 nowych przypadków** łącznie; powyższe zbiory nachodzą na siebie, nie sumować.
- `git diff --check` PASS; `pip check`: No broken requirements found.
  Ostrzeżenia AnyIO CallSpec2 i Starlette/httpx pozostają; brak zmian zależności.
- Końcowy CI dokładnego HEAD jest warunkiem PASS kodu; wynik po push w Checks PR #3
  i raporcie rozmowy. Nie zastępujemy go historycznym CI punktu wejściowego.

## Odczyty / BLOCKED

Środowisko running/connected, current observations, policy revision 5.
TCP domains/ip_ranges puste, VPN=false: **0 prób SSH, 0 SELECT-ów**. Zgoda A aktualna.
Nie próbowano MCP SQL jako obejścia. Prywatne identyfikatory wymagają potwierdzenia.
Render get_postgres: PG17 available, Frankfurt, 0.1c-256mb, 1 GB, HA=false;
bezpieczne metadata w provider-readonly.json, bez połączeń/PII/sekretów.
Tool nie podaje latest recoverable point/WAL lag. Nie odświeżano listy eksportów ani
nie tworzono kopii/restore/PITR. Historyczne AVAILABLE i stary eksport nie dowodzą RPO60.

**Brak podstaw do READY operacyjnego:** aktualne SQL/004/konta/17 hashów, RPO60,
trwały niezależny magazyn/klucz/retencja, artefakt/env rollbacku oraz dowód końca starych
procesów pozostają otwarte. Pauza/drain przygotowane w kodzie nie są wykonanym rollout.

## NEXT / zgody

Bieżąca czynność: zatwierdzić ograniczony grant TCP Codex do ssh.frankfurt.render.com:22.
Po nim sprawdzić host/tożsamość/kanał i prywatne konta, następnie tylko 4 zatwierdzone SELECT-y.
Najprostszy recovery: obecny PITR, najpierw dowód latest point przez Recovery/support
właściciela, potem osobno zatwierdzony izolowany test w RPO. Nie kupować upgrade bez dowodu
potrzeby; nie uruchomiono testu ani kontaktu z supportem. Szczegóły w ROLLOUT.md.
Merge/deploy, zmiana WORKER_PAUSED na produkcji, nowe eksporty/PITR/koszty i Meta
wymagają osobnej zgody. Żadna z tych operacji nie została wykonana.

Pliki: backend/worker.py, backend/worker_control.py, .env.example,
tests/test_worker_lifecycle.py, tests/test_supervise.py, RESUME.md i dokumenty sesji 011.
Commit raportu: `git log -1 --format=%H -- docs/sessions/session-011/REPORT.md`.
Zmiany wyłącznie Focus 3.0; Focus 1.0/2.0 niezmienione. Bez danych produkcyjnych,
DELETE/cleanup, konfiguracji sieci/sekretów/Render, migracji produkcji i rzeczywistych DM.
**Szacunek: nadal 5 sesji podstawowych + ≥1 DM**. Brak redukcji za poprawki kodu przy
otwartych bramkach operacyjnych. Nie deklarujemy działania w tle.
