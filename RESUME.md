# Wznowienie — sesja026, osobna automatyzacja Codex

Data: 2026-11-09, Europe/Warsaw.
Gałąź: `feat/session-026-codex-automation`, z main
`d15265b26524d594bdbcb4bc6b63fcbc398a1424`.
Nie jest to gałąź wydania 3.0.4; PR #3 i `fix/3.0.4-meta-validation` pozostawiono bez zmian.
Wejściowy PR #3 Draft, e37ce5d1ce807b47af18e3354c3232296b8b26c6, oba CI42686949414/42686938187 SUCCESS.

## Co zapisano

- `.github/workflows/codex-issues.yml`: oficjalny Codex, dwie flagi default OFF,
  osobna zgoda na hash Issue, role, environment approval, atomowa rezerwacja,
  walidacja patcha, Draft PR, pełny job CI i raport commit/Issue.
- `.github/workflows/codex-policy-tests.yml`: bezpłatna walidacja polityki bez sekretów.
- `scripts/codex_automation/pipeline.py`: zaufany kontroler.
- `tests/automation/test_policy.py`: 30 testów; API fixture, lokalny git i 20 równoległych rezerwacji.
- Raport i instrukcja: `docs/reports/CODEX_AUTOMATION.md`.
- Prawdziwe nieszkodliwe Issue #5: https://github.com/artgawlik-ui/ai-focus-3-0/issues/5,
  BLOCKED, bez komendy zatwierdzającej lub wywołania modelu.

## Dowody

`python -m unittest discover -s tests/automation -v`: 30PASS/0FAIL/0SKIP.
`actionlint1.7.12 -shellcheck= ...`: PASS, release checksum zweryfikowany.
Compileall, parser YAML i diff-check PASS. Końcowe SHA/Checks sprawdzić w GitHub dla tej
oddzielnej gałęzi. Nie utożsamiać CI aplikacji/testów polityki z E2E wykonawcy Codex.

## Potwierdzony zapis GitHub

Kod cc514f344eb2dedfe605d7b64b9f3cc7d0a6b657, osobny Draft PR #6:
https://github.com/artgawlik-ui/ai-focus-3-0/pull/6.
Pełne CI42701994238(push)/42702077788(PR) SUCCESS:110 PASS,35 subtests,2warnings;
build,Chromium/WebKit PASS, oba audyty0 znanych podatności.
Policy CI42701994538/42702077857 SUCCESS (30 nowych metod testowych).
Żaden workflow wykonawcy nie był uruchomiony. PR #3 Draft/merged=false/HEADe37ce5d bez zmian.
To CI gałęzi opartej na main, nie ponowny test 380 przypadków niepołączonego wydania3.0.4.
Końcowy commit dokumentacyjny ma własne SHA i Checks — sprawdzić przy wznowieniu.

## Ograniczenia i decyzje właściciela

Nie wymagać teraz klucza API. Nie obchodzić403 przy ustawieniach Actions/runners/secrets.
Nie aktywować flag, płatnego API ani produkcji. Brak merge/deploy/Render/SQL/eksportu/
restore/zmian klientów/Meta/DM/Google. Focus1.0/2.0 i PR #3 bez zmian.
Prawdziwy E2E **BLOCKED** do autoryzowanego wykonawcy i zgody kosztowej oraz świadomej
instalacji workflow na main. Nie zastępować Codexa mockiem i nie deklarować PASS E2E.

## Następny krok

Przeczytać raport026, sprawdzić HEAD i końcowe Checks nowego Draft PR automatyzacji.
Jeżeli zielone — czekać na decyzję właściciela o późniejszej instalacji i koszcie.
Nie wykonywać powtórnych symulacyjnych sesji ani zmieniać PR #3. Jedno polecenie wznowienia:
„Wznów sesję026 na feat/session-026-codex-automation; przeczytaj RESUME.md oraz
CODEX_AUTOMATION.md, sprawdź końcowe CI; bez aktywacji, merge, deployu i zmian PR #3”.
