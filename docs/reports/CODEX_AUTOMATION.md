# Sesja 026 — automatyzacja Fokus → GitHub → Codex

Data sprawdzenia: **9 listopada 2026, Europe/Warsaw**.

**Kod i testy lokalne: PASS. Aktywacja i rzeczywisty E2E: BLOCKED.**
Nie uruchomiono modelu ani płatnego API. Nie ma zastępczego, symulowanego wykonawcy.
Stan końcowego CI i SHA należy odczytać z Checks gałęzi tego raportu; lokalne testy
nie są dowodem uruchomienia workflow przez GitHub ani wykonania zadania przez Codexa.

## Izolacja i punkt wejścia

- Oddzielna gałąź `feat/session-026-codex-automation`, z `main`
  `d15265b26524d594bdbcb4bc6b63fcbc398a1424`.
- PR #3 pozostaje Draft, HEAD wejściowy
  `e37ce5d1ce807b47af18e3354c3232296b8b26c6`.
  Jego zakończone CI: [42686949414](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42686949414)
  i [42686938187](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42686938187), SUCCESS.
- Przeczytano README z main oraz RESUME i PRODUCTION_READINESS z gałęzi wydania.
  W przeszukanym workspace nie znaleziono AGENTS.md. Nie zmieniono gałęzi wydania,
  kodu CRM, jego zależności, migracji, danych ani ustawień Render. ZIP-y użytkownika nietknięte.
- To osobny system zlecania prac programistycznych, a nie worker agenta sprzedaży.
  Produkcyjne bramki 3.0.4 nadal BLOCKED; niniejsze testy ich nie zamykają.
- Repozytorium jest **publiczne**. Issue, komentarze, patche i raporty muszą zawierać
  tylko informacje przeznaczone do publikacji, bez danych klientów i sekretów.

## Oficjalny wykonawca i dokumentacja

Sprawdzono oficjalne README, action.yml, security.md oraz tag `v1`
[openai/codex-action](https://github.com/openai/codex-action).
Akcja instaluje prawdziwy Codex CLI i korzysta z Responses API; wymaga autoryzowanego
klucza dostawcy. Dostęp do ChatGPT/Connectora sam nie potwierdza tej autoryzacji.
W konfiguracji przypięto commit akcji
`bdf19a4a223ec2549a3e2274a0cf61556bc07675` i CLI `0.167.0`
(odczytano oficjalny release `rust-v0.167.0`). Przypięty action.yml potwierdza
`permission-profile`, `safety-strategy`, `prompt-file`, `codex-version` i `model`.
Profil `:workspace` wymaga CLI >=0.138.0; nie łączymy go z legacy `sandbox`/`--full-auto`.
Pozostałe akcje także są przypięte pełnymi SHA.

Źródła, sprawdzone 2026-11-09:
- [Oficjalna akcja](https://github.com/openai/codex-action/blob/bdf19a4a223ec2549a3e2274a0cf61556bc07675/action.yml)
  i [zasady bezpieczeństwa](https://github.com/openai/codex-action/blob/main/docs/security.md).
- [Uprawnienia Codexa](https://developers.openai.com/codex/permissions).
- [GitHub — zdarzenia, issue_comment](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#issue_comment):
  workflow musi istnieć na domyślnej gałęzi. Samo Issue nie uruchamia Codexa.
- [GitHub — wyzwalanie workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow):
  GITHUB_TOKEN nie wywołuje zwykłego push CI. Aktualna dokumentacja opisuje także
  PR otwarte przez ten token jako wymagające zatwierdzenia uruchomienia workflow.
  Dlatego pełna walidacja jest osobnym jobem tego samego zaufanego workflow;
  wynik trafia na SHA kandydata jako status `codex/validation`, bez zależności
  od dodatkowego PR eventu, PAT lub nowej aplikacji GitHub.
- [Cennik OpenAI](https://developers.openai.com/api/docs/pricing),
  [rozliczanie GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Przepływ i granice zaufania

1. Fokus tworzy Issue poprzez dostępne, autoryzowane narzędzie GitHub. To tylko zadanie.
2. Uprawniona osoba osobno zatwierdza dokładny tytuł i treść:
   `/codex approve <SHA-256>`. Wymagane prawa write/maintain/admin zarówno autora
   Issue, autora komentarza, jak i osoby ponawiającej workflow. Nie używamy samych
   `author_association`, etykiety ani treści nieautoryzowanych komentarzy jako zgody.
3. Admission pobiera aktualne Issue, sprawdza hash, status open, rozmiar i tożsamość
   repozytorium. Odrzuca PR, komentarze edytowane, zmienioną treść i inne gałęzie niż main.
   Sprawdza obecność reguły required reviewers dla właściciela `artgawlik-ui`
   w środowisku `codex-development`. Błędy API, w tym 403, kończą etap — bez obejścia.
4. Atomowe `POST /git/refs` rezerwuje `codex/issue-N` na bieżącym SHA main.
   Istniejący ref blokuje kolejny start, także po błędzie lub restarcie workflow.
   Nie ma schematu podatnego na wyścig GET-then-create. `concurrency` dodatkowo
   serializuje wykonania tego samego Issue; GitHub nie gwarantuje globalnego FIFO.
   Różne zatwierdzone zadania mogą działać równolegle — brak nieograniczonej,
   samodzielnie generowanej kolejki i brak automatycznego ponawiania płatnego wykonawcy.
5. Snapshot zatwierdzenia i prompt są artefaktem admission. Codex pracuje na zaufanym
   main/SHA, z `contents: read`, bez zapisanego tokenu checkout, bez produkcyjnych
   sekretów, w `:workspace`, `drop-sudo`, na jednorazowym runnerze Ubuntu.
   OPENAI_API_KEY trafia tylko do oficjalnej akcji. Brak klucza/modelu kończy job.
6. Propozycja Codexa jest niezaufanym patchem. Publikowanie następuje na świeżym
   runnerze z oryginalnym kontrolerem i metadanymi zatwierdzenia przekazanymi
   wyłącznie przez wyjścia zaufanego joba admission, bez wykonywania kodu kandydata.
   Publikacja nie pobiera snapshotu z artefaktu; próba podmiany artefaktu nie zmienia
   numeru Issue, SHA, gałęzi ani hasha zgody. Ponownie sprawdzana jest zgoda oraz stan zarezerwowanej gałęzi.
7. Dozwolone: `backend/`, `frontend/src/`, `tests/`, `docs/`, ograniczone rozszerzenia.
   Limit 30 plików / 200 000 bajtów. Zablokowane: `.github`, instrukcje AGENTS,
   ukryte pliki, zależności, skrypty operacyjne, migracje, Render, symlinki,
   submoduły, patche binarne i wykryte wzorce sekretów. Wyłączono wykrywanie
   rename, by kontrolować również chronioną ścieżkę źródłową.
8. Zwykły fast-forward push, bez force. Powstaje osobny Draft PR do main.
   Pełna walidacja działa na dokładnym SHA opublikowanym przez kontroler:
   syntetyczny PostgreSQL 17, backend, frontend/build, Chromium, WebKit, audyty.
   Job walidacji ma tylko contents: read, bez API key i bez sekretów produkcyjnych.
9. Osobny zaufany job raportujący zapisuje status commit i komentarz Issue.
   Nie publikuje swobodnej odpowiedzi modelu, promptu, patcha ani wyjątków dostawcy.
   Nie wykonuje się merge, deploy, approve PR ani operacji produkcyjnych.

Po awarii rezerwacja pozostaje. To celowe **at-most-one admission**, nie deklaracja
exactly-once w rozproszonym systemie. Przy timeout po POST/push należy sprawdzić ref,
run i istniejący PR, a nie uruchamiać ponownie. Operator może zlecić nowe Issue po
uzgodnieniu stanu. Kontroler nigdy sam nie usuwa ani nie nadpisuje rezerwacji.
Wyłączenie flag blokuje przyszłe przyjęcia; uruchomiony już job trzeba dodatkowo
anulować w Actions. Wyłączenie flag nie cofa zużytych tokenów API.

## Konfiguracja i uprawnienia — przygotowane, nie aktywowane

| Ustawienie | Domyślne zachowanie / przeznaczenie |
|---|---|
| `FOCUS_CODEX_AUTOMATION_ENABLED` (repo variable) | brak/puste/inne niż dokładnie `true` = OFF |
| `FOCUS_CODEX_COSTS_APPROVED` (repo variable) | niezależna bramka kosztowa; brak/puste/inne = OFF |
| `FOCUS_CODEX_MODEL` (repo variable) | wymagany późniejszy, świadomie wybrany model; brak = BLOCKED |
| `OPENAI_API_KEY` (environment secret) | wyłącznie `codex-development`, osobny projekt deweloperski; nie wymagany teraz |
| `codex-development` | required reviewer: właściciel `artgawlik-ui`; brak reguły blokuje admission |

Globalnie `permissions: {}`. Minimalne rozszerzenia per job:
- admission: contents write do jednego ref, issues read i actions read do weryfikacji;
- Codex: contents read;
- publish: contents write, pull-requests write, issues read, statuses write;
- validation: contents read;
- report: contents read, issues write, statuses write.

GITHUB_TOKEN nie daje ograniczenia contents write do pojedynczego ref — zakres ten
ogranicza zaufany kontroler i brak wykonania kandydata w jobie publikacji.
Nie dodano PAT, klucza SSH, klienta Render ani połączeń do produkcyjnej bazy.

Odczyt repo metadanych potwierdził publiczne repo, default main i raportowane
uprawnienia push/admin oraz `allow_auto_merge=false`. Odczyty ustawień workflow,
runnerów self-hosted i listy sekretów zakończyły się **403 Resource not accessible by
integration**. Nie próbowano innych tożsamości ani obejścia. Stąd nie wolno twierdzić,
że sekret jest pusty, runnerów brak lub ustawienia zezwalają na tworzenie PR.
Dotychczasowy udany CI potwierdza działanie runnerów użytych w tamtych uruchomieniach,
nie dostępność środowiska wykonawczego przyszłego Codexa.

## Testy i dowody

- `python -m unittest discover -s tests/automation -v`: **32 PASS, 0 FAIL, 0 SKIP**.
  Fixture API i syntetyczne zadania; brak prawdziwych wywołań Codex/Meta/Google/Render.
- 20 równoległych prób rezerwacji z fixture atomowego API: 1 zwycięzca, 19 odrzuceń.
  To test kontrolera, nie test współbieżności prawdziwego API GitHub.
- Rzeczywiste lokalne git init/apply/commit/push do tymczasowego bare repo potwierdza
  publikowanie zaakceptowanego patcha; API PR/statusów w tym teście pozostaje fixture.
- Sprawdzono odmowę uprawnień, stare hashe, podszywanie się, rerun actor, 403,
  fail-closed flagi, blokadę kosztową, ścieżki/rename, symlinki, limity i wzorce sekretów.
- `actionlint 1.7.12 -shellcheck= ...`: **PASS** dla obu workflow; pobrany oficjalny
  artefakt zweryfikowany SHA-256 według release checksums. Shellcheck nie uruchamiano.
- `python -m compileall -q scripts/codex_automation tests/automation`: PASS.
- YAML obu workflow parsuje się poprawnie. `git diff --check`: PASS.
- Utworzono jedno prawdziwe, nieszkodliwe [Issue #5](https://github.com/artgawlik-ui/ai-focus-3-0/issues/5).
  Bez komendy zatwierdzającej, bez opłat. Potwierdza zapis zadania w GitHub,
  nie odbiór i realizację przez Codexa.
- **Prawdziwy E2E Issue → Codex → zmiana → Draft PR → CI: BLOCKED / niewykonany.**

## Potwierdzony CI pierwszej wersji kodu (przed utwardzeniem granicy artefaktów)

Kod: **`cc514f344eb2dedfe605d7b64b9f3cc7d0a6b657`**, [osobny Draft PR #6](https://github.com/artgawlik-ui/ai-focus-3-0/pull/6).
Pełny CI push [42701994238](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42701994238)
i PR [42702077788](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42702077788): **SUCCESS**.
Log push/job129448812191: **110 passed, 2 warnings, 35 subtests passed, 24.31 s**.
110 obejmuje 30 nowych testów automatyzacji; subtestów nie doliczamy jako osobnych metod.
Build PASS, `chromium-desktop: PASS`, `webkit-iphone: PASS`, npm audit: 0 vulnerabilities,
pip-audit: No known vulnerabilities found. To gałąź z main, nie zestaw 380 testów
niepołączonego wydania z PR #3.
Workflow polityki: push [42701994538](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42701994538)
i PR [42702077857](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42702077857): **SUCCESS**.
Po tym CI utwardzono publikację: brak zaufania do snapshotów z artefaktów. Dwa nowe
testy (32 łącznie) oraz test lokalnego git z celowo podmienionym snapshotem PASS.
Poprawiona wersja wymaga własnego pełnego CI; nie przypisujemy jej wyniku cc514f3.
Nie wystartował workflow wykonawcy Codex. PR #3 ponownie potwierdzony Draft, merged=false,
HEAD e37ce5d niezmieniony. Końcowy SHA i jego własne Checks należy potwierdzić przed zamknięciem sesji.

## Końcowy kod po utwardzeniu — potwierdzony CI

**`35a83b6e7cd837497190406d724bc056de51c6d2`**:
- pełny push [42703140324](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42703140324) SUCCESS;
- pełny PR [42703150599](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42703150599) SUCCESS;
- polityka push [42703140392](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42703140392)
  i PR [42703150536](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42703150536) SUCCESS.

Log push/job129452864260: **112 passed, 2 warnings, 35 subtests passed, 25.34 s**.
32 nowe metody testowe automatyzacji. Build PASS, Chromium desktop PASS, WebKit iPhone PASS,
npm audit: 0 vulnerabilities; pip-audit: No known vulnerabilities found.
To weryfikacja kodu i regresji na syntetycznych danych; **E2E prawdziwego Codexa nadal BLOCKED**.
Kolejny commit zapisuje wyłącznie dowody w raporcie/RESUME i checklistę bezpiecznej instalacji.
Nie zmienia implementacji. Jego SHA i Checks są dostępne w osobnym Draft PR #6.

## Koszty — szacunek do późniejszej decyzji

Teraz: **0 wywołań płatnego modelu**, brak nowych usług Render i zmiany kosztu hostingu.
GitHub standard hosted runners w publicznym repo są objęte zasadami bezpłatnego
użycia; sprawdzić plan, storage i limity przed aktywacją. Artefakty mają retencję 1 dzień.
API rozlicza rzeczywiste tokeny, nie abonament tej automatyzacji.
Przykład z aktualnego cennika: `gpt-5.3-codex`, Standard, 1 mln tokenów:
input **1,75 USD**, output **14 USD**, cached input **0,175 USD**.
50 000 input + 10 000 output ≈ **0,2275 USD/zadanie**; 100 takich zadań ≈ **22,75 USD**.
To przykład arytmetyczny, nie limit ani prognoza rzeczywistego zużycia: powtarzany
kontekst, rozumowanie, liczba tur, wybrany model i dodatki mogą zwiększyć koszt.
Przed włączeniem należy zatwierdzić model i budżet osobnego projektu API oraz ustawić
limity/rate limits i alerty u dostawcy. Timeout 15 min nie jest twardym limitem kosztu,
a alert budżetowy nie musi blokować rozliczeń. Niczego nie aktywowano ani nie zakupiono.

## Instrukcja późniejszej aktywacji — niczego z tej listy teraz nie wykonano

1. Właściciel przegląda **osobny** Draft PR automatyzacji. Po zatwierdzeniu instalacji
   dopiero świadomy merge tego PR umieszcza workflow na main. PR #3 nie jest częścią tej operacji.
   Przed merge potwierdzić, że aktualizacja main nie uruchomi zewnętrznego autodeploy
   Render. Jeżeli uruchomi — STOP i osobna decyzja właściciela; nie zmieniać teraz ustawień Render.
2. GitHub → Settings → Actions → General: potwierdzić dostęp do standardowych runnerów,
   allowlist akcji przypiętych SHA i możliwość tworzenia PR przez GITHUB_TOKEN.
   Nie włączać auto-merge ani deploy. Dopuszczenie automatycznego tworzenia PR nie
   upoważnia kodu do zatwierdzania lub scalania — takich operacji nie ma w kontrolerze.
3. Settings → Environments → `codex-development`: ustawić required reviewer właściciela
   i ograniczyć deployment branches do main. Nie dodawać sekretów produkcyjnych.
   Po osobnej zgodzie kosztowej umieścić tylko OPENAI_API_KEY osobnego projektu dev.
   Wartości wpisywać w oficjalnym panelu; nie przesyłać ich w rozmowie ani Issue.
4. Settings → Secrets and variables → Actions → Variables: wybrać zatwierdzony model.
   Obie flagi pozostawić false do zgody na pierwszy realny test. Potem ustawić je
   na dokładnie `true` w ramach osobnej, świadomej aktywacji.
5. Dopiero wtedy zatwierdzić Issue #5 zgodnie z procedurą poniżej i przejść required
   environment review. Monitorować prawdziwy run, Draft PR, `codex/validation` i rachunek.
6. Sprawdzić, że prawdziwy Codex dodał oczekiwany plik dokumentacji Issue #5 i spełnił
   jego kryteria. PASS E2E dopiero po dowodzie rzeczywistego Codex run + SHA zmiany + Draft PR + pełne CI.
   Brak którejkolwiek części = BLOCKED. Nie stosować symulowanego fallbacku.

## Instrukcja dla Fokus

- Użyć narzędzia GitHub z prawem tworzenia Issue. Jeżeli Connector oferuje tylko odczyt
  lub odmawia zapisu, zgłosić brak uprawnienia; nie zakładać, że komentarz uruchomi Codexa.
- Tworzyć małe, precyzyjne Issue: cel, dozwolone pliki, kryteria akceptacji, testy,
  ograniczenia. Bez danych klientów, sekretów, operacji produkcyjnych i instrukcji wdrożenia.
- Po uzyskaniu osobnej zgody na konkretne zadanie pobrać aktualny JSON Issue i obliczyć
  hash funkcją z tej samej wersji zaufanego kontrolera:
  `gh api repos/artgawlik-ui/ai-focus-3-0/issues/N | python scripts/codex_automation/pipeline.py digest`.
  Hash obejmuje tytuł i body, nie komentarze. Nie obliczać go z podglądu/renderowanego Markdown.
- Uprawniony zlecający dodaje dokładnie `/codex approve HASH`, jako nowy komentarz.
  Zmiana body wymaga ponownego zatwierdzenia; nie kopiować instrukcji innych komentarzy.
- Śledzić run i status `codex/validation`, powiązany Draft PR oraz komentarz raportujący.
  Sam powstały Draft PR/pending status nie jest sukcesem. Nie scalać ani wdrażać.
- Po błędzie nie usuwać automatycznie gałęzi rezerwacji i nie ponawiać płatnego runu.
  Ustalić stan i przekazać operatorowi konkretną przyczynę/URL; nowe Issue po rozstrzygnięciu.

## Ryzyka i statusy końcowe

| Element | Status | Brakujący dowód / następny krok |
|---|---|---|
| Kontroler i walidacja | PASS | 32 nowe testy + actionlint; kod35a83b6: pełny CI SUCCESS, 112 PASS |
| Zapis nieszkodliwego zadania | PASS | Issue #5 istnieje; bez zgody uruchomienia |
| Instalacja workflow na main | BLOCKED | osobny przegląd i zgoda na merge; teraz wyłącznie branch/Draft PR |
| Ustawienia Actions/runners/secrets | BLOCKED | operator potwierdza w panelu; integracja zwraca 403 |
| Wykonawca i koszty | BLOCKED | autoryzowany dev API key/model, budżet i zgoda; nie wymagane teraz |
| Environment protection | BLOCKED | potwierdzona reguła właściciela, main-only i test odmowy bez niej |
| Prawdziwy test E2E | BLOCKED | pierwszy realny Codex run dopiero po powyższych warunkach |
| Produkcja Ai Focus 3.0.4 | BLOCKED osobno | dotychczasowe bramki SQL/RPO/kopie/rollback/handoff, bez zmian |

Filtr sekretów jest heurystyczny; nie dowodzi wykrycia każdego hasła lub danych osobowych.
Sandbox i zatwierdzenie nie eliminują prompt injection; wymagany przegląd kodu przez człowieka.
GitHub nie gwarantuje ciągłego uptime/FIFO. Cancel/awaria publish może pozostawić sam ref
lub commit bez PR — operator uzgadnia stan. Repozytorium publiczne nie nadaje się do
przekazywania prywatnych poleceń/danych CRM. Nie przyznano dostępu do Render/SQL/SSH.
RESUME tej osobnej gałęzi dotyczy026; przy późniejszym łączeniu z wydaniem trzeba
zachować również aktualny punkt wznowienia PR #3, bez zastępowania jego historii.

## Lista zmienionych plików sesji026

- `.github/workflows/codex-issues.yml` — przyjmowanie, oficjalny wykonawca, publikacja, CI, raport.
- `.github/workflows/codex-policy-tests.yml` — testy bez sekretów.
- `scripts/codex_automation/pipeline.py` — zaufany kontroler.
- `tests/automation/test_policy.py` — 32 testy polityki i lokalnego git.
- `docs/reports/CODEX_AUTOMATION.md` — dowody i instrukcja administratora/Fokus.
- `RESUME.md` — niezależny punkt wznowienia automatyzacji.
- `tests/test_meta_303.py` — deterministyczny zegar istniejącego testu ostrzeżeń, bez zmian runtime.

## Niejednakowy wynik końcowych CI i poprawka deterministyczności

Dokumentacyjny7a7f2f7: PR42703924171 SUCCESS, ale push42703915281 FAILURE.
Log job129455552253:111passed/1failed — `test_owner_diagnostics_and_approved_retention`,
pusty caplog zamiast ostrzeżenia. Nie uznano całego SHA za zielone.
Test resetował `_last_alert=0`, podczas gdy kod ma cooldown60s liczony monotonicznie.
Na świeżym runnerze z uptime<60s pierwsze ostrzeżenie nie jest jeszcze emitowane.
Kontrolowana reprodukcja lokalna prawdziwej funkcji maintenance (DB fixture):
10s→0 alertów;120s→1;179.9s→1;180s→2. Bez produkcji lub połączeń Meta.
Próba lokalnego całego testu SQLite zawisła w TestClient i została zakończona;
nie zaliczono jej jako PASS. Pełne PostgreSQL/build/przeglądarki/audyty potwierdza CI.

W `tests/test_meta_303.py` wstrzyknięto zegar tylko modułu inbox:120/179.9/180s.
Zachowano retencję, RBAC i brak treści w logach; dodano asercje cooldownu i ponownego
ostrzeżenia na granicy60s. Bez usunięcia testów, skipów, zmiany timeoutów lub kodu
produkcyjnego Meta.32 testy automatyzacji i actionlint ponownie PASS.
Nowa wersja wymaga własnego pełnego CI obu zdarzeń.
