# RAPORT AI FOCUS 3.0.4 — SESJA 008

Data: 5 listopada 2026. **Wydanie: BLOCKED.**

## DONE — wyniki i zakres

- Lokalny HEAD i GitHub PR HEAD: 33790a728493e3a19d97fc455b1f76be6d452ce0.
  PR #3 open/Draft, bez merge; baza d15265b26524d594bdbcb4bc6b63fcbc398a1424.
  `github_get_pr_info` i `github_fetch_commit_workflow_runs` potwierdziły stan;
  [CI checkpointu: success](https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/42062017735).
- Przeczytano RESUME, raport/prośbę A sesji 007, SELECTS sesji 005, recovery sesji 006
  i globalny release gate. Brak nowych zdalnych commitów na wejściu. Zachowano wcześniejszą
  lokalną aktualizację zgody A; jej nieaktualne ograniczenie push zastąpiono zgodą sesji 008.
  Trzech nieśledzonych archiwów nie otwierano, nie zmieniano i nie publikowano.
- `environment_status`: running/connected, observations_current=true, revision 5.
  Odczyt `/etc/codex/network-policy.json`: TCP domains/ip_ranges puste, VPN=false.
  **Brak potwierdzonego grantu TCP. Nie wykonano próby SSH ani zapytań SQL.**
- Zapisano decyzje właściciela: A udzielona, kontrolowany worker zatwierdzony,
  RPO 60 minut nadal wymagane. Nie jest potrzebna ponowna zgoda A.
- Naprawiono rzeczywisty błąd `scripts/supervise.py`: start dzieci przeniesiono do
  try/finally. Błąd uruchomienia workera lub opcjonalnego backupu powoduje zamknięcie
  wcześniej uruchomionych dzieci. Import modułu nie startuje już procesów.
  Obsługa sygnałów jest przywracana po zakończeniu. Polecenia, flagi i limit 25 s zachowane.
  To poprawka kandydata, nie dowód zachowania już uruchomionej produkcji.

## Testy i dowody

1. Kod bazowy odczytany przez `git show 33790a7:scripts/supervise.py` uruchomiono
   wyłącznie w harnessie z mockami Popen/signal, symulując błąd drugiego startu:
   **terminate_calls=0, wait_calls=0**. Brak prawdziwych procesów potomnych.
2. `.venv/bin/python -m pytest -q tests/test_supervise.py tests/test_data_release_gate.py tests/test_offsite_backup.py`:
   **12 passed, 0 failed, 0 skipped**; 5 nowych testów supervisora, 7 istniejących.
   Scenariusze: błąd startu workera, awaria dziecka, SIGTERM, limit czasu/kill,
   błąd startu opcjonalnego backupu, sygnał w trakcie startu. Nie wykonywano backupu:
   test offsite używa syntetycznych bajtów i mocków uploadu/backup.
3. Pierwsza próba: 10 passed/1 failed — mock nie odzwierciedlał zakończenia dziecka po
   terminate (obserwowano dwie próby terminate). Poprawiono model mocka i dodano osobny
   test sygnału podczas startu; końcowe 12/12 PASS.
4. `.venv/bin/python -m pip check`: **No broken requirements found**.
   `git diff --check`: PASS. Brak zmian zależności, modeli i migracji.
5. Jedno ostrzeżenie środowiskowe: AnyIO używa aliasu pytest CallSpec2 przewidzianego
   do usunięcia w pytest 10; testy przechodzą, nie zmieniano zależności.

Lokalne testy tej sesji nie korzystały z bazy, sieci ani rzeczywistych procesów.
Nie powtarzano zakończonego restore, nie tworzono lokalnej ani Render recovery DB.
Standardowy istniejący workflow GitHub po push sprawdza regresję na izolowanej,
syntetycznej usłudze PostgreSQL runnera (nie kopii produkcji i nie zasobie Render), build,
Chromium/WebKit i audyty. Jego wynik należy przypisać do dokładnego SHA w Checks;
nie jest potwierdzeniem produkcji. 11 testów operatorskiego cleanup pozostaje wykluczonych.

## BLOCKED — bramki operacyjne

| Bramka | Stan |
|---|---|
| Zgoda A / kontrolowany worker | Zatwierdzone; zamknięta blokada decyzji, nie weryfikacja operacyjna |
| Wewnętrzny kanał SQL | BLOCKED — brak grantu TCP, host key/autoryzacja niezweryfikowane |
| Bieżące 004/konta/sesje/liczności/SHA 17 tabel/inbox/retencja | BLOCKED — 0 SELECT-ów, prywatne tożsamości niepotwierdzone |
| RPO ≤3600 s | BLOCKED — brak dowodu latest point i skutecznego recovery w wymaganym oknie |
| Trwały niezależny szyfrowany magazyn/klucz/retencja | Niepotwierdzone; bez nowych kopii/eksportów |
| Artefakt/env rollbacku i rozliczenie zapisów rolling deploy | Niepotwierdzone przed przyszłym wydaniem |
| Merge/deploy/Meta | Niezatwierdzone, niewykonane |

Nie odświeżano metadata Render tylko po to, aby powtórzyć wynik sesji 007.
Dane z 1 listopada 17 tabel/23 rekordy/004 to historyczny snapshot, nie obecna produkcja.
PITR AVAILABLE nie potwierdza RPO. Worker nadal może tworzyć szkice/statusy i wykonywać
retencję przy Meta OFF; ta poprawka nie zmienia jego zachowania i nie zatrzymuje zapisów.

## NEXT — jedna bieżąca czynność właściciela

**W konfiguracji środowiska Codex zatwierdzić ograniczony grant TCP do
`ssh.frankfurt.render.com:22`.** Nie zmieniać publicznej allowlisty PostgreSQL ani tworzyć
kluczy/ról/sekretów. Potem sprawdzić tożsamość hosta i autoryzację istniejącego kanału;
jeśli nie da się ich zweryfikować, STOP. Zgoda A nie obejmuje zmian dostępu.

Po potwierdzeniu kanału i prywatnych tożsamości: dokładnie cztery SELECT-y sesji 005,
bez dodatkowych zapytań i danych osobowych w raporcie. Dalsze recovery/koszty/eksporty,
zmiany konfiguracji, merge/deploy i aktywacja Meta wymagają osobnej decyzji.

## Zapis i bezpieczeństwo

Pliki sesji: scripts/supervise.py, tests/test_supervise.py, RESUME.md,
docs/meta/3.0.4/RELEASE_GATE.md, docs/sessions/session-008/ACCEPTANCE.md i REPORT.md.
SHA zapisu: `git log -1 --format=%H -- docs/sessions/session-008/REPORT.md`.
Końcowe CI sprawdzić dla HEAD PR #3; raport rozmowy podaje wynik po push.

Nie zmieniano produkcji/Render/klientów/sieci/sekretów/Meta. Bez DELETE/cleanup,
migracji produkcyjnych, eksportu/restore/PITR, restartu, merge/deploy, nowych płatnych
zasobów i wiadomości. Focus 1.0/2.0 niezmienione. PR ma pozostać Draft.
**Szacunek: 5 sesji podstawowych + ≥1 DM**, bez obniżenia za częściową poprawkę kodu.
Nie deklarujemy pracy w tle ani gotowości produkcyjnej.
