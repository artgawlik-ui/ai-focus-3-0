# Issue #14 — smoke test gotowego obrazu rollbacku

Zakres: osobna gałąź z `56d6f8326b6afdaf2890dac0471dac835082cbab` (PR #9).
Nie zmienia normalnego startupu ani PR #3/#6/#8/#9. Bez Render i rzeczywistych danych.

## Nowy dowód, który ma powstać w CI

Poprzednie 394 testy i build obrazu nie potwierdzały jego uruchomienia. Nowy krok
istniejącego workflow buduje obraz, po czym uruchamia **ten sam image ID**, z jego
domyślnym CMD i bez montowania kodu do kontenera API. Nie zastępuje API atrapą.

- Osobny tymczasowy PostgreSQL 17, sieć Docker `--internal`, brak publikowanych portów.
- Brak dziedziczenia DATABASE_URL, sekretów aplikacji i cookies hosta. Proxy w testowych
  kontenerach wyłączone. Docker CLI wskazuje wyłącznie lokalny socket.
- Fixture przygotowuje schemat 007 oraz fikcyjne konta/sesje, salony, wizytę, zaległe
  zadanie, oczekujący job i inbox z terminem retencji. To jedyne migracje i zapisy testu.
  API nie dostaje plików migracji. Nie używa kopii produkcji ani zgody A.
- Rzeczywiste HTTP: health/root, istniejące sesje, RBAC właściciel/handlowiec,
  odmowa sesji wyłączonej/wygasłej/brakującej, dozwolone odczyty i no-store.
- Zapis, login/logout, eksport, zadania i integracje zwracają 503. TCP WebSocket upgrade
  nie może otrzymać 101. Kod ASGI w tym samym obrazie osobno potwierdza close 1008;
  nie utożsamiamy tego z kodem ramki na przewodzie, gdy Uvicorn nie ma biblioteki WS.
- Osobny probe w tym samym obrazie sprawdza SQLSTATE 25006, wymuszenie flag OFF,
  nieuprzywilejowany UID, faktyczny PID1 i brak procesów potomnych workera/supervisora.
  Obraz nie zawiera migracji ani startupów bootstrapu/workera.
- 21 liczności/SHA-256 przed/po identyczne, również dla canary job/inbox/task.
- Ten sam domyślny obraz odmawia startu bez zgody oraz na markerach 004 i 006.
  Każdy przypadek porównuje fingerprinty; log odmowy ma wyłącznie stały komunikat.
- Czyszczenie wyłącznie zasobów z losową etykietą tego testu, bez prune/wspólnych usług.

## Reprodukcja na zatwierdzonym lokalnym Dockerze

Wymagania: Python 3.12, Docker z lokalnym socketem, repozytorium tego SHA.
Poniższe komendy pobierają wyłącznie publiczny obraz/deps budowy i tworzą syntetyczne
zasoby lokalnego demona; nie wywołują usług aplikacji ani Render. Nie wykonywać ich
na współdzielonym produkcyjnym daemonie.

```sh
docker --host=unix:///var/run/docker.sock pull postgres:17
docker --host=unix:///var/run/docker.sock build -f Dockerfile.rollback -t focus3-rollback-validation .
python -m tests.rollback_container_smoke --image focus3-rollback-validation --results test-results/rollback-container-smoke.json
```

Na runnerze GitHub obraz postgres:17 już istnieje dzięki dotychczasowej usłudze CI.
Harness używa `--pull=never`, bez registry push i bez host network. Kontener API ma
limit 512 MB/1 CPU, PostgreSQL 512 MB/1 CPU i dane wyłącznie w tmpfs; to kontrola
poprawności, nie benchmark pojemności Render. Wszystkie zasoby są usuwane po teście.
Przerwanie całego runnera wymaga wyczyszczenia tylko zasobów z jego etykietą, nigdy prune.

W środowisku Codexa buildy mogą wymagać konfiguracji CA z instrukcji runtime. Nie
wyłączać TLS ani nie zmieniać sieci w celu obejścia blokady. Lokalny odczyt Docker info
tej sesji został odrzucony przez sandbox; **nie uznano lokalnego runtime za PASS**.

## Artefakt i status

Workflow `Verify Focus 3` zapisuje `test-results/rollback-container-smoke.json`
w istniejącym artefakcie `verification-results`. Zawiera image ID, image ID PG,
testowany checkout SHA, nazwy zaliczonych kontroli, syntetyczne fingerprinty,
stały zanonimizowany komunikat odmowy i wynik cleanup. Bez surowych wyjątków/logów,
połączeń i wartości sesji. Status PASS wymaga rzeczywistego zakończenia smoke i cleanup.
Przy błędzie pole `stage` wskazuje etap; brak dowodu to BLOCKED, nie symulacja sukcesu.

Lokalnie: 5 nowych testów bezpieczeństwa harnessu PASS. Końcowy wynik runtime i pełnego
CI konkretnego SHA należy odczytać z Checks Draft PR i podać w Issue #14/#12.
Ponowna pełna regresja jest uzasadniona zmianą workflow i dodaniem testów.

Nawet po zielonym smoke rozdzielamy:

| Bramka | Znaczenie |
|---|---|
| Container runtime PASS | Wyłącznie gdy test uruchomił obraz i zakończył wszystkie kontrole |
| Render artifact availability BLOCKED | Brak zachowanego, uruchamialnego celu z potwierdzonym start/env w Render |
| Production handoff BLOCKED | Nie wykonano zatrzymania wszystkich starych writerów i kontrolowanego przełączenia |

Ten JSON nie jest zachowanym obrazem ani digestem opublikowanym w registry. Nie
uruchamia rollout, nie akceptuje degradacji loginu/UI/zapisów i nie potwierdza RPO,
produkcyjnych kont ani integralności. Nie wykonano skanu bazowego OS. Odmowa zapisu
dotyczy połączeń profilu, a nie zmiany uprawnień roli PostgreSQL.
