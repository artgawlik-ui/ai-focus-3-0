# RAPORT AI FOCUS 3.0.4 — SESJA 003

Data: 1 listopada 2026, Europe/Warsaw. Gałąź fix/3.0.4-meta-validation.

## Cel i warunki rozpoczęcia

Najnowsza instrukcja właściciela:
https://github.com/artgawlik-ui/ai-focus-3-0/pull/3#issuecomment-6560169007
Bez automatycznego wejścia w produkcję: runbook dostępu, lokalny dry-run wydania,
osobne decyzje A/B/C i plan Meta Development vs Live. Przeczytano dokumenty sesji 002.

Krok zerowy: GitHub i lokalny HEAD 76330d05353f9f54c3a3371500fd658b7bb2e766;
PR open/Draft, bez merge. Obie kontrole tego SHA odczytane ponownie:
- https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41322287902 — push success.
- https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41322291961 — PR success.
Pobrano ponownie log pierwszego runu: 142 passed, 2 warnings; Chromium i WebKit PASS.
Liczba należy do tego SHA i nie jest potwierdzeniem stanu uruchomionej produkcji.

## Zadania, kod i commity

- 045c4ad: kryteria przed implementacją, ACCEPTANCE.md.
- b44ecc9: scripts/release_dry_run.py i tests/test_release_dry_run.py.
- Dokumentacja: ACCESS_RUNBOOK.md, DECISIONS.md, META_TEST_PLAN.md, LOCAL_RELEASE.md,
  synthetic-profile.json, dry-run-result.json, evidence.json, diff-main.txt i ten REPORT.md.
  SHA raportu: git log tego katalogu; lista sesji: git diff --name-only 76330d0 HEAD.

Offline dry-run nie ma transportu HTTP/SQL, nie odczytuje środowiska produkcji i nie zmienia
flag. Sprawdza wszystkie flagi osobno, wersję 3.0.4, schema 004 i syntetyczne warunki profilu.
Nieprawidłowa/pusta/true flaga blokuje profil. Brak zmiennej to default false przy legacy OFF.
Wynik PASS_LOCAL oznacza wyłącznie spójność dostarczonego profilu; pola restore/rollback
w JSON są fixture, nie dowodem kopii produkcyjnej ani dostępu do niej.
Wynik zawsze ma production_verified=false i wszystkie zgody operacyjne false.

Test lokalny integracyjny sprawdza rzeczywisty kod aplikacji na danych syntetycznych:
CRM/health/login/logout działają, prywatne API bez sesji 401, OAuth/webhook/subscription
wyłączone, bezpośredni transport DM 403. Deaktywacja syntetycznego konta technicznego
unieważnia jego sesję, a właściciel zachowuje dostęp i może zalogować się ponownie.
Nie dotknięto rzeczywistego konta technicznego.

Runbook określa zatwierdzony klucz i host key, ograniczony grant TCP, istniejącą usługę,
transfer przypiętych narzędzi dopiero po zgodzie i dokładny output READ ONLY/warunki STOP.
Nie deklaruje read-only RBAC samego SSH. Kontrola transakcyjna narzędzia nie odbiera
szerszych uprawnień użytkownika SSH/DB; dedykowana rola wymagałaby osobnej zmiany produkcji.

DECISIONS.md rozdziela zgody A (odczyt/kopie), B (późniejszy cleanup aktualnego zakresu),
C (merge/deploy konkretnego SHA Meta OFF). Każda ma cel, warunki, kroki, ryzyko i rollback.
Żadna zgoda nie jest domniemana. Nie żądamy w rozmowie sekretów ani nie tworzymy klucza
ulotnego, którego trwałość nie została uzgodniona.

## Testy i dowody

- pytest tests/test_release_dry_run.py tests/test_readonly_preflight.py:
  **12 passed, 0 failed/errors/skipped**, 5,52 s. Wyłącznie lokalny PostgreSQL focus3_test.
- Po doprecyzowaniu typu wyjątku transportu: pytest tests/test_release_dry_run.py:
  **3 passed, 0 failed/errors/skipped**, 1,76 s. Powtórka podzbioru, nie 15 unikalnych testów.
- python -m scripts.release_dry_run --profile docs/sessions/session-003/synthetic-profile.json:
  **PASS_LOCAL**, wynik w dry-run-result.json; brak zezwoleń na działania produkcyjne.
- python -m alembic heads: **004 (head)**. Brak nowych migracji/zmian schematu.
- git diff --check: PASS.
- Bazowy pełny CI 142 i przeglądarki ponownie zweryfikowano w logach; nie uruchamiano
  lokalnie niezmienionego build/restore/E2E bez potrzeby. Pełny CI nowego HEAD uruchamia
  regresję, frontend, Chromium/WebKit i audyty. Końcowy wynik widoczny w Checks PR #3;
  starego wyniku nie przedstawiamy jako wyniku nowego SHA.
Komendy i agregaty w evidence.json. Dwa znane ostrzeżenia zależności pytest/Starlette;
żaden test tej sesji nie wymagał naprawy. Brak testu fizycznego iPhone'a w tej sesji.

## Status

| Zakres | Wynik | Znaczenie |
|---|---|---|
| Krok zerowy / historyczne CI dokładnego SHA | PASS | odczyt GitHub i logów |
| Lokalny Meta OFF dry-run / smoke | PASS lokalnie | 3 nowe testy plus regresja READ ONLY |
| Dostęp READ ONLY / SQL produkcji | READY runbook / BLOCKED wykonanie | brak zatwierdzonego kanału/grantu i osobnej zgody |
| Release 3.0.4 | READY przygotowanie / BLOCKED produkcja | brak aktualnej kontroli danych/kopii/kont/rollbacku i zgody |
| Recovery / retencja | READY procedura / BLOCKED rzeczywiste potwierdzenie | nie odczytywano prywatnych kopii ani magazynu |
| Meta Development OAuth | READY plan / BLOCKED realny test | brak osobnej autoryzacji/konta/callbacka testowego |
| Meta Live webhook | BLOCKED | aktualna dokumentacja wymaga Live; osobna decyzja i warunki Meta |
| Komunikacja wychodząca / etap 7 | nie rozpoczęta, BLOCKED | odrębna wyraźna zgoda; DM nieuruchomione |

Brak PASS production i brak deklaracji pełnej gotowości operacyjnej.

## Blokady i minimalne czynności właściciela

1. Osobno rozpatrzyć zgodę A. Potem **Render Account settings → SSH Public Keys →
   + Add SSH Public Key** dla zatwierdzonego klucza. Prywatny klucz pozostaje w magazynie.
2. Administrator środowiska: ograniczony grant TCP ssh.frankfurt.render.com:22.
   Bieżąca polityka odczytana lokalnie: puste domains/ip_ranges, VPN false.
   Nie próbowano SSH, nie otwierano publicznej allowlisty i nie omijano proxy.
3. Po skonfigurowaniu kanału osobno dopuścić transfer/wykonanie narzędzia i kontrolę kopii.
   Bieżący zakres historycznych 13 rekordów pozostaje NIEPOTWIERDZONY.
4. Wskazać trwały magazyn i niezależny klucz do aktualnego backupu/undo, uzgodnić retencję.
   Kod offsite wymaga potwierdzonego lifecycle 30 dni; nie twierdzimy, że jest skonfigurowany.
   Nie aktywowano magazynu ani paid PITR. RPO/RTO nie potwierdzono.
5. B i C rozpatrywać oddzielnie dopiero po spełnieniu opisanych bramek; żadnego cleanup
   ani deployu w ramach tej sesji. Plan Meta wymaga innych, odrębnych zgód.

## Ograniczenia i bezpieczeństwo

Nie łączono się z Render, bazą produkcyjną ani publiczną aplikacją.
Nie czytano .render-auth, kluczy prywatnych, historycznych kopii ani archiwów.
Nie wykonano produkcyjnego DELETE/COMMIT, merge, deploy, migracji ani zmian środowiska.
Nie wykonano realnego OAuth/Graph/Instagram/DM, nie zmieniano Live ani flag Meta.
Nie utworzono płatnych zasobów, nie zmieniano sekretów, firewall ani uprawnień.
Focus 1.0 i 2.0 niezmienione; zmieniono wyłącznie pliki tego repozytorium Focus 3.0,
lista zakresu w diff-main.txt. Archiwa nieśledzone pozostały nietknięte.
Źródła Meta/Render wykorzystano z oficjalnego odczytu sesji 002 tego samego dnia;
nie udajemy ponownego odczytu paneli ani rzeczywistych testów usług.

## Licznik i wznowienie

**Pozostaje 5 sesji podstawowych + co najmniej 1 DM. Licznik bez zmian:**
nie zamknięto żadnej bramki operacyjnej; lokalne przygotowanie nie zastępuje jej wykonania.
Szacunek zależy od dostępu, decyzji i warunków Meta, nie jest obietnicą terminu.

Wznowienie: sprawdzić HEAD/checks i najnowszy komentarz PR #3, przeczytać ten raport.
Bez nowych zgód zachować zakaz połączeń z produkcją; kontynuować tylko niezależne
zadania lokalne. Po zgodzie A i skonfigurowaniu kanału zastosować ACCESS_RUNBOOK.md;
BLOCKED przy dowolnej rozbieżności, bez aktualizacji manifestu w celu wymuszenia PASS.
B i C nie wynikają ze zgody A. Testy bazodanowe wyłącznie sekwencyjne na focus3_test.
Nie deklarujemy działania w tle po zakończeniu sesji.
