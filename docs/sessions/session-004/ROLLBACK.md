# Plan rollbacku — wyłącznie przygotowany, bez wykonania

## Punkt wyjścia rzeczywiście odczytany

Usługa ai-focus-3-0 / srv-dbh1rk6tlv9c73dloq20, workspace My Workspace.
W dniu 1 listopada 2026 API potwierdziło live:
- deploy dep-dbjhl6jbc2fs73crj65g;
- commit d15265b26524d594bdbcb4bc6b63fcbc398a1424;
- autodeploy no, repo artgawlik-ui/ai-focus-3-0, branch main, Frankfurt, 1 instancja;
- healthCheckPath /api/health, publiczna wersja 3.0.3 i HTTP 200.
Ten deploy jest docelowym punktem powrotu po przyszłym zatwierdzonym wydaniu.
Status live nie jest potwierdzeniem nieograniczonej retencji artefaktu do przyszłego rollbacku.
API/MCP nie udostępnia osobnej flagi dostępności historycznego obrazu. Nie uruchomiono
rollbacku ani przebudowy w celu jej sprawdzenia. Przed użyciem sprawdzić dostępność.

## Warunki przed przyszłym deployem

1. Osobna zgoda na merge/deploy konkretnego SHA; zielone checks dokładnego kandydata.
2. Zatwierdzony kanał READ ONLY: produkcyjny Alembic 004 i zgodny schemat, aktualne konta
   i zakres danych. Obecna próba SQL zablokowana; nie otwierać publicznej allowlisty.
3. Świeża zaszyfrowana kopia poza ulotnym serwerem i sprawdzony restore wszystkich 17 tabel;
   hash/liczności/schemat, niezależny trwały klucz, retencja i rejestry usunięć/opt-out.
4. Zapisany aktualny rollback target i potwierdzona dostępność artefaktu. Plan awaryjny:
   rebuild tego samego SHA tylko po zgodzie, z kontrolą zależności, schematu i konfiguracji.
5. Wszystkie flagi Meta oraz niezależny DM OFF, płatne AI OFF; ocena istniejącego agenta
   szkiców. AGENT_V2_ENABLED jest obecnie ON, nie zmieniono tego ustawienia.
6. Start aplikacji wykonuje alembic upgrade head. Mimo braku nowych migracji schema 004
   musi zostać potwierdzony przed deployem, aby nie wykonać niezatwierdzonej migracji.

## Wykonanie tylko po osobnej zgodzie

W razie nieudanego przyszłego wydania: zatrzymać dalsze operacje, zachować bezpieczną
diagnostykę, ponownie sprawdzić target, następnie Render Dashboard → usługa → Deploys
→ właściwy deploy → Rollback → potwierdzenie. Żadnego triggera nie wykonano w tej sesji.
Po operacji: faktyczny live commit/deploy, health/HTTPS, prywatne API 401, właściciel,
Meta OFF i integralność danych w zatwierdzonym oknie bez zapisów.
Nie nadpisywać PostgreSQL, nie wykonywać downgrade ani DROP; rollback aplikacji nie
cofa migracji, dysków, wiadomości i działań zewnętrznych. Nie uruchamiać cleanup salonu.

## Bieżące oficjalne zasady Render

https://render.com/docs/rollbacks.md — odczyt HTTP 200 w tej sesji:
- zachowana jest ustalona liczba ostatnich artefaktów zależna od planu workspace;
- środowisko, start command i health check są odtwarzane z wybranego deployu na czas
  rollbacku; aktualna konfiguracja usługi nie jest nadpisywana dla przyszłych wdrożeń;
- compute plan i dyski pozostają bieżące; env groups mają osobne reguły;
- rollback w Dashboard wyłącza autodeploy; po dowolnej metodzie odczytać faktyczny stan.
Dlatego dzisiejszy odczyt env-vars nie dowodzi pełnej konfiguracji docelowego rollbacku.
Nie ustalono nowej retencji/cennika, nie zmieniano workspace ani zasobów.
