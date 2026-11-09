# Sesja027 — zamknięcie możliwych luk wydania

**Produkcja: BLOCKED. Kod wariantu007 ma pełny CI5e4188a SUCCESS;
końcowy dopisek/odmowa WebSocket wymagają własnego CI przed zamknięciem sesji.**
Baza e37ce5d1ce807b47af18e3354c3232296b8b26c6, PR3Draft;
CI42686949414/42686938187 SUCCESS (380 testów, build,Chromium/WebKit,audyty).
Nie powtarzano dawnych symulacji024–025 jako nowych dowodów produkcji.

## Nowe rzeczywiste wyniki

- Świeży Render control-plane GET: My Workspace potwierdzone wcześniej przez właściciela,
  zasoby z [provider-readonly.json](provider-readonly.json). Live d15265b,
  autoDeploy=no,1instancja,Starter0.5c/512MB,PG17 available/0.1c256MB/1GB.
  Publiczna allowlista nadal pusta; nie odczytywano wartości środowiska/sekretów.
- Obserwacje środowiska current/enforced revision5: TCP=[],VPN=false, brak skonfigurowanych
  tożsamości. Nie ma zatwierdzonego działającego wewnętrznego kanału ani prywatnego
  potwierdzenia kont. **0SSH,0SELECT produkcyjnych**. Pakiet005 nietknięty,
  SHA795af23ad5acb4d0af451f683e10c9cdfcdcdd10d64bd0f58d6d5b29782815fb.
- Nie użyto MCP SQL jako obejścia: ma nowe połączenie per zapytanie i nie potwierdza
  zatwierdzonego kanału ani wspólnego snapshotu4SELECT. Zgoda A nie obejmuje007.
- Metadane PG nie zawierają recovery/latest point/WAL lag. Database available ≠ PITR
  AVAILABLE ≠ skuteczne odtworzenie z RPO≤60min. Bieżący RPO nadal niepotwierdzony.
  Historyczny dump1listopada (004/17tabel/23rekordy,odtworzony przez właściciela)
  zachowuje wartość historycznego testu, ale nie potwierdza obecnych danych/RPO.
- Ponownie odczytano oficjalne Markdown Render: backups,rollbacks,private-network,
  maintenance-mode (HTTP200, treść przeczytana). PITR płatnych baz ciągły, okno3/7dni
  wgplanworkspace; ostatnie10min niedostępne; eksporty7dni. Samo ograniczenie UI
  nie dowodzi lag≤60min. Nie pobierano ani nie tworzono eksportów/recovery instancji.
- Brak nowych dowodów niezależnego obiektu kopii, retencji, wersji klucza i odzyskania
  go przez operatora. Dzienny opt-in offsite w kodzie nie realizuje sam RPO60.

## Rzeczywista luka i poprawka

024 dowiódł, że standardowy startup d15265b odrzuca007. Istniał jedynie test odczytu
starego API z pominiętym startupem i podmienioną zależnością auth. Nie istniał gotowy,
fail-closed profil startowy. Dodano:
- `scripts/rollback_readonly.py`: jawna zgoda FOCUS_READONLY_ROLLBACK_APPROVED=true,
  PG17/007/21tabel, readonly każdej sesji DB, ograniczony GET/HEAD, istniejąca autoryzacja
  i RBAC, brak nowego logowania, workerów, bootstrapu, migracji i integracji.
- `Dockerfile.rollback`: oddzielny obraz tylko API; nie pakuje migracji lub skryptów
  uruchamiających background. Normalny Dockerfile, start.sh i supervisor bez zmian.
- 14 nowych testów: defaultOFF/niepoprawne URL/SSL/options/ścieżki/process guard;
  prawdziwy procesAPI i syntetycznyPG007, owner/rep/disabled, SQLSTATE25006 przy próbie
  UPDATE, zapis503 i identyczność wszystkich21count/SHA.004/006 odrzucane.
- CI zbudował też pełny obraz awaryjny bez jego uruchamiania/push/deploy. Obraz runnera
  jest efemeryczny; NIE dowodzi zachowania go w Render ani dostępności rollbacku.
- Przeniesiono wyłącznie znaną deterministyczną korektę zegara istniejącego testu
  z026 (120/179.9/180s); nie zmieniono PR6/#8, runtime Meta, timeoutów i skipów.

To **ograniczony awaryjny odczyt**, nie pełny powrót funkcjonalny: nowe login/logout,
zapisy, nativekalendarz/zadania i UI niedostępne. Nie przedstawiać go jako zatwierdzonego
rozwiązania biznesowego. Owner musi zaakceptować degradację i zachować zweryfikowany
artefakt/start/env; nadal BLOCKED dla produkcji. Aktualna004 nie uruchomi tego profilu007.

## Testy przed CI

`pytest -q tests/test_rollback_readonly.py -k 'not real_api'`: **11PASS,3deselected**
(te3przypadki czekają na syntetycznyPG wCI; nie zaliczono ich do lokalnego PASS).
Compileall i diff-check PASS. Kontrola lokalnego Docker przez minimalny grant socketu
zakończyła się błędem sandbox bwrap, zanim ruszyło polecenie. Nie restartowano demona,
nie zmieniano uprawnień i nie obchodzono izolacji. Pełny CI ma dostępny istniejący PG17
oraz Docker i sprawdzi rzeczywiste przypadki procesu/obrazu. Do tego czasu027 kod IN PROGRESS.

## Plan i operacje wymagające odrębnej zgody

[ROLLOUT.md](ROLLOUT.md): maintenance blokuje tylko publiczny ruch; worker/prywatne API
nadal mogą pisać. Nowy worker paused przed startem, dowód wyjścia WSZYSTKICH starych,
kontrola zadań/retencji/count/hash, zgoda na resume. Usunięcie pliku pauzy nie znosi
WORKER_PAUSED=true; plan rozróżnia obie metody. Start.sh sam uruchamia Alembic/bootstrap.

[PRODUCTION_READINESS](../../reports/PRODUCTION_READINESS.md) zawiera aktualną macierz
PASS/BLOCKED i konkretne instrukcje operatora. Nie zamknięto bramek SQL/kont/RPO/kopii/
klucza/artefaktu/handoff/zatwierdzenia. Funkcje normalnej aplikacji mają dowody syntetyczne
wCI; nie testowano rzeczywistego logowania/zapisów i nie aktywowano native007 na produkcji.
Nie zmieniono produkcji, klientów, Render/sieci/sekretów ani PR6/#8. Zero merge/deploy,
produkcjiDDL/DML,export/restore/PITR,nowychzasobów/kosztów i Meta/DM/Google.

## Potwierdzony pełny CI wariantu027

Commit5e4188af1166623fb3f3598b7bd7bd38fd59cf84, osobny [Draft PR #9](https://github.com/artgawlik-ui/ai-focus-3-0/pull/9),
basefix/3.0.4-meta-validation.
[Push42713625735](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42713625735)
i [PR42713880948](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42713880948)
**SUCCESS**:394PASS/0FAIL/0SKIP,2warnings,169.75s wpush.14nowych testów,
w tym3 rzeczywiste przypadkiPG/procesu. Wcześniejsze380 wykonano jako regresję
zmienionego kodu, nie jako nowe sesje symulacyjne. Build frontendu,Chromium/WebKit
i oba audyty PASS,0znanych podatności zależności. Pełny buildDockerfile.rollback PASS.
ImageID zrunnera:sha256:4520aa14b0a22e01f8115721199754f293581ca050ceb6eaf516dc0069e4f082.
To nie digest opublikowanego obrazu ani artefakt zachowany wRender. Nie testowano
bootu tej konkretnej konteneryzacji; testy uruchomiły rzeczywisty moduł/API naPG17.
Nie wykonywano skanu podatności bazowego systemuOS. Zachować te granice dowodów.

Po tym CI dodano odmowę WebSocket do guardu, aby tylko lifespan mógł korzystać
z nie-HTTP ścieżki app; test polityki obejmuje też ten protokół. Reszta zachowania
bez zmian. Końcowy SHA/CI znajduje się w opisie PR #9 i Checks; przed końcowym
raportem weryfikujemy oba wymagane uruchomienia. Produkcja pozostaje BLOCKED.
