# Issue #7 — ręczny workflow Fokus → GitHub → Codex

Data: 9 listopada 2026, Europe/Warsaw.
**Test ręcznego przekazania Issue → istniejący Codex → zmiana → Draft PR → CI → raport: PASS**
dla opublikowanego kodu7f88096. Nie jest to test automatycznego wykonawcy lub niezależnego
przeglądu przez Fokus. Końcowy dopisek dokumentacyjny i poprawny zapis placeholdera YAML
mają własny SHA/Checks, sprawdzane przed zamknięciem zadania i raportowane w Issue #7.

## Autoryzacja i izolacja

Właściciel ręcznie polecił bieżącej sesji Codexa odczytać i wykonać Issue #7.
Odczyt Issue potwierdził autora `artgawlik-ui`, status open; odrębny odczyt uprawnień
`GET /repos/artgawlik-ui/ai-focus-3-0/collaborators/artgawlik-ui/permission`
zwrócił admin. Nie pobierano instrukcji z komentarzy do wykonania.
To istniejąca, autoryzowana sesja Codexa, a nie wywołanie API OpenAI lub dodatkowy bot.
Snapshot tytułu/body Issue (kanoniczny JSON dwóch pól, UTF-8): SHA-256
`1ea6d9470afb609df41560ef5a93c81ffea8c1af948fb78a330ead0c0f32ee0e`.

Gałąź: `docs/issue-7-manual-codex-workflow`, od main
`d15265b26524d594bdbcb4bc6b63fcbc398a1424`.
Przeczytano README i punkty wznowienia/gotowości istniejącego projektu.
AGENTS.md nie znaleziono w przeszukanym workspace. Nie naruszono zmian użytkownika.
Stan wejściowy i późniejszy odczyt muszą się zgadzać:

| PR | Draft | HEAD | updated_at przed pracą |
|---|---|---|---|
| #3 | true | e37ce5d1ce807b47af18e3354c3232296b8b26c6 | 2026-11-09T19:55:46Z |
| #6 | true | 02449d5f1c0d61ef0bb9ff5cb589ac56aeffb92e | 2026-11-09T21:49:49Z |

Nie wykonywano merge ani aktualizacji tych PR. Nie odczytywano ani nie zmieniano Render,
produkcji, bazy, sekretów, sieci lub konfiguracji integracji. Brak nowych lub produkcyjnych migracji, restore,
eksportu, cleanup, operacji Meta/DM/Google i Focus 1.0/2.0. Istniejący CI przygotowuje
wyłącznie efemeryczną bazę syntetyczną swoim dotychczasowym krokiem Alembic; nie uruchamiamy
bezpośrednich migracji ani połączeń do rzeczywistych baz.

## Dostarczone elementy

- [Instrukcja](../workflows/MANUAL_CODEX.md) opisuje właściciela, Fokus, GitHub, Codexa,
  testy, raportowanie, wznowienie i proceduralną ochronę przed drugim wykonaniem.
- [Formularz Issue](../../.github/ISSUE_TEMPLATE/manual-codex-task.yml) zawiera wymagane
  cel/bazę/zakres/akceptację/testy oraz obowiązkowe ograniczenia bezpieczeństwa.
- [Krótki prompt](../workflows/CODEX_START_PROMPT.md) wymaga tylko numeru zadania;
  właściciel nie musi kopiować całego opisu do Codexa.
- [Nieszkodliwy artefakt](../workflows/examples/MANUAL_HANDOFF_SMOKE.md) powstał
  w tej rzeczywistej, ręcznie rozpoczętej sesji dla zadania dokumentacyjnego.
- README udostępnia instrukcję; RESUME dotyczy wyłącznie tej osobnej gałęzi.

Nie dodano workflow GitHub Actions, executora, automatycznej kolejki, schedulera,
klucza API ani zależności. Pełne istniejące CI jest walidacją zmian po push/PR,
a nie mechanizmem uruchamiającym Codexa. Formularz jest plikiem do przeglądu na gałęzi;
nie pojawia się jeszcze jako zainstalowany formularz domyślnej gałęzi bez zgody na merge.

## Nieszkodliwy test ręczny i granice dowodów

| Krok | Dowód przed końcowym CI | Status |
|---|---|---|
| Issue istnieje i ma dozwolony zakres | rzeczywisty odczyt [#7](https://github.com/artgawlik-ui/ai-focus-3-0/issues/7), autor/admin potwierdzeni | PASS |
| Właściciel uruchomił Codexa ręcznie | bieżąca dyspozycja właściciela w sesji Codexa: odczyt #7, dokumentacja/test/Draft PR | PASS w tej sesji |
| Codex wykonał nieszkodliwą zmianę | instrukcja, formularz, prompt i plik przykładowy w osobnej gałęzi | PASS lokalny |
| Zapis GitHub, Draft PR i CI dokładnego SHA | [Draft PR #8](https://github.com/artgawlik-ui/ai-focus-3-0/pull/8), SHA7f880960b34bbcc0fee47693ea030bb9998b06c0, oba CI SUCCESS | PASS |
| Raport w GitHub do odczytu przez Fokus | [komentarz Issue #7](https://github.com/artgawlik-ui/ai-focus-3-0/issues/7#issuecomment-6752742954), zapis rzeczywiście potwierdzony | PASS |
| Osobna instancja Fokus samodzielnie utworzyła Issue i niezależnie oceniła wynik | nie obserwowano tych operacji; nie przypisujemy ich sobie | NIEZWERYFIKOWANE |

To test ręcznego uruchomienia istniejącego Codexa. Nie użyto mocka wykonawcy ani nie
przedstawiamy tego jako testu automatyzacji PR #6; jej rzeczywisty E2E nadal BLOCKED.
Późniejsza niezależna weryfikacja przez Fokus wymaga odczytu raportu i Checks w GitHub.

## Walidacja i uzasadnienie korekty istniejącego testu

Dokumentacja nie wymaga nowych unit testów odtwarzających jej treść. Wykonujemy walidację
formularza YAML, odnośników i diff-check oraz pełne istniejące CI: syntetyczny PostgreSQL,
backend, frontend/build, Chromium/WebKit i audyty zależności. Wyniki CI dopisujemy po wykonaniu.

Do tej gałęzi przeniesiono **wyłącznie hunk testowy** z wcześniej zweryfikowanego PR #6:
`tests/test_meta_303.py`, kontrolowany zegar 120/179.9/180 s w teście alertu retencji.
Powód techniczny jest znany i odtworzony w026: stary test resetował _last_alert=0,
a na świeżym runnerze z uptime<60 s nie powstaje jeszcze ostrzeżenie. CI push42703915281
miał111PASS/1FAIL, mimo że równoległy PR był zielony. Nie kopiujemy implementacji automatyzacji
ani dokumentów PR #6 i nie zmieniamy tamtej gałęzi. Zachowano retencję, RBAC i kontrolę
braku payloadu w logach; dodano asercje cooldownu i ponownego alertu po60s.
Brak skipów, usuniętych scenariuszy, wydłużonych timeoutów i zmian runtime Meta.
Nie liczymy tej korekty jako nowej funkcji aplikacji lub nowego testu jednostkowego.

## Koszty, blokady i dalsze użycie

Bez API OpenAI, bez OPENAI_API_KEY i bez zakupu nowych usług. Korzystanie z Codexa podlega
istniejącej autoryzacji/planowi/limitom właściciela; nie obiecujemy nielimitowanego użycia.
Nie potrzeba dostępu do produkcji ani sekretów Render. Nie obchodzimy403.

Manualny workflow nie zapewnia automatycznej deduplikacji między dwoma ręcznie
uruchomionymi sesjami; właściciel sprawdza jeden aktywny PR i koordynuje przejęcie.
Nie ma automatycznego retry ani pracy po zakończeniu sesji. Produkcyjne bramki3.0.4
pozostają niezależnie BLOCKED. Nic w tym raporcie nie upoważnia do merge/deployu.

Po zapisaniu wyników właściciel/Fokus może zlecać kolejne bezpieczne zadania, tworząc
Issue i ręcznie otwierając sesję Codexa krótkim promptem. Instalacja formularza na main,
wydanie aplikacji i aktywacja automatyzacji są osobnymi decyzjami, niewykonanymi tutaj.

Walidacja lokalna: parser YAML PASS (6 pól, wymagane odpowiedzi i checkboxy),
13 lokalnych odnośników w6plikach Markdown PASS; `git diff --check` PASS.
`git diff -- .github/workflows` jest pusty: nie dodano ani nie zmieniono wykonawcy.
0 nowych metod testów jednostkowych; pełny dotychczasowy zestaw uruchamia CI.

## Dowody wykonania i wynik CI

Commit implementacyjny **7f880960b34bbcc0fee47693ea030bb9998b06c0** jest w GitHub.
[CI push42708132895](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42708132895)
i [CI PR42708200556](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42708200556):
**SUCCESS**. Job129470269285: `80 passed, 2 warnings in 28.09s`.
Build PASS, `chromium-desktop: PASS`, `webkit-iphone: PASS`; npm audit0podatności,
pip-audit `No known vulnerabilities found`. WebKit jest testem przeglądarkowym,
nie testem na fizycznym iPhonie. To80 testów aktualnego main, nie112 z PR #6
ani380 z niepołączonego wydania PR #3; żadnych testów nie usunięto.

Końcowa walidacja formularza uwzględnia również pełny tekst placeholdera PR #3/#6:
wartość ujęto w cudzysłowy, aby YAML nie traktował # jako początku komentarza.
Parser/pola/checkboxy,13linków i diff-check PASS. Osiem zmienionych plików: formularz,
README,RESUME,instrukcja,prompt,artefakt,ten raport oraz deterministyczny test.
Bez zmian `.github/workflows`, runtime lub zależności.

Prawdziwy test ręcznej sesji nie jest zablokowany przez brak API OpenAI. Osobna ocena
przez Fokus pozostaje **NIEZWERYFIKOWANA**, a instalacja formularza na main **READY do
osobnej decyzji**, niewykonana. Nie ma zgody na merge/deploy. Automatyzacja PR #6
nadal nieaktywna; jej E2E jest osobno BLOCKED. Wynik dokładnego końcowego SHA jest
opublikowany po zakończeniu jego CI w powyższym komentarzu i opisie Draft PR #8.
