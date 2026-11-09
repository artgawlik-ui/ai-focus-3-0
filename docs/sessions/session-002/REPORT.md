# RAPORT AI FOCUS 3.0.4 — SESJA 002

Data: 1 listopada 2026, Europe/Warsaw. Gałąź fix/3.0.4-meta-validation.

## Cel i źródło instrukcji

Najnowszy komentarz właściciela w PR #3:
https://github.com/artgawlik-ui/ai-focus-3-0/pull/3#issuecomment-6559995956
Przygotować bezpieczny preflight READ ONLY i instrukcję odblokowania SQL/Meta.
Komentarz warunkuje rzeczywisty odczyt skonfigurowaniem autoryzowanego kanału.
W tej sesji nie wykonywano połączeń z Render, produkcyjnym PostgreSQL ani aplikacją.

Krok zerowy: HEAD lokalny/GitHub a9e2fab7fd4e6603ddffc0099141b7fafe7bf5be;
PR open, Draft, niepołączony. Obie kontrole tego SHA ponownie odczytane z GitHub:
- PR: https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41320281910 — success.
- push: https://github.com/artgawlik-ui/ai-focus-3-0/actions/runs/41320277697 — success.
Nie zakładano sukcesu na podstawie poprzedniego raportu. Nie zmieniono historii gałęzi.

## Zrealizowane zadania i commity

- dd206ca: kryteria akceptacji przed implementacją, ACCEPTANCE.md.
- 78b9cb9: scripts/readonly_preflight.py oraz tests/test_readonly_preflight.py.
- Dokumentacja tej sesji: OWNER_SETUP.md, RELEASE_GATE.md, documentation-evidence.json,
  evidence.json, diff-main.txt i niniejszy REPORT.md. Commit dokumentacji: git log tego katalogu.

Preflight nie importuje aplikacji/modeli ORM, nie uruchamia bootstrapu, migracji, workerów,
backupu ani DM. Wymusza read-only już w opcjach połączenia, następnie BEGIN TRANSACTION
ISOLATION LEVEL REPEATABLE READ READ ONLY. Limit połączenia 5 s, statement 5 s,
lock 1 s, idle-in-transaction 10 s; zakończenie ROLLBACK i zamknięcie połączenia także po błędzie.
Domyślny dopuszczony cel: lokalny focus3_test. Przyszły wewnętrzny kanał wymaga jawnego
przełącznika i odpowiedniej nazwy hosta/bazy; flaga nie zastępuje uprawnień ani zgody właściciela.
Publiczne hosty bazy, query/fragment w URL i niejednoznaczne cele są odrzucane.
Porównuje zakres/ID/hash/schema/revision/zależności z manifestem w pamięci, ale stdout
zawiera tylko zgodność, liczby i statusy. Każda rozbieżność -> BLOCKED.
Opcjonalne zatwierdzone ID kont pozwalają sprawdzić nieaktywność konta technicznego,
brak wszystkich jego sesji i aktywność/rolę właściciela; brak ID -> not_checked.
Aktywność właściciela w SQL nie jest dowodem udanego logowania.

## Wyniki testów i dowody

Dokładne agregaty/komendy w evidence.json; wszystkie dane testowe syntetyczne.
- pytest tests/test_readonly_preflight.py tests/test_salon_cleanup.py:
  **20 passed, 0 failed/errors/skipped** (8,80 s).
- Po dodaniu kontroli PostgreSQL major=17: pytest tests/test_readonly_preflight.py:
  **9 passed, 0 failed/errors/skipped**. To powtórzenie części zestawu, nie 29 unikalnych testów.
- Test rzeczywistego lokalnego PostgreSQL potwierdza READ ONLY/repeatable read i identyczność
  count/SHA wszystkich 17 tabel przed/po. Odrzucane zmiany ID/liczby/hash/schematu/revision,
  powiązania Meta/aktywne joby, niebezpieczne konta i hosty; wyjście nie ujawnia identyfikatorów.
- python -m alembic heads: **004 (head)**; brak nowej migracji i zmian schematu.
- git diff --check: PASS.
- Pełny backend/build/Chromium/WebKit/audyty na bazowym SHA miały odczytany PASS.
  Lokalnie nie powtarzano niezmienionego build/E2E i odtwarzania kopii bez potrzeby;
  CI nowego HEAD uruchamia pełny zestaw. Ostateczny wynik sprawdzić w Checks PR #3.
- Nie stwierdzono błędu w testach tej sesji. Dwa ostrzeżenia zależności pytest/Starlette
  są znane z sesji 001; nie dowodzą nowych podatności. Audyt zależności wykona CI.

## Oficjalna dokumentacja — wynik rzeczywistego odczytu

GET publicznych dokumentów (nie Graph/OAuth API), HTTP 200, daty i SHA w
 documentation-evidence.json; linki i kroki właściciela w OWNER_SETUP.md.
Potwierdzono: Unified Login oparty o Facebook Login for Business, Meta App ID/Secret,
config_id, minimalne instagram_basic/instagram_manage_messages, SUAT i
/me/assigned_instagram_accounts, role testerów, Standard/Advanced Access i menu panelu.
Kod wskazuje Graph v26.0; dokumenty setup nie mają numeru wersji. Nie wykonywano Graph.

Istotna granica: aktualny webhook setup wymaga published/Live dla notifications app users;
Development OAuth test z rolą nie potwierdza rzeczywistego dostarczania webhooków.
Nie zmieniamy trybu aplikacji, nie wnioskujemy o Advanced Access ani nie aktywujemy callbacka.
Wymóg Live/business verification blokuje realny test w narzuconym wyłącznie Development
bez osobnego uzgodnienia dozwolonego scenariusza. Nie uznano fixture za test Meta.

## Status kryteriów / etapów

| Zakres | Status | Dowód lub blokada |
|---|---|---|
| Krok zerowy, head/checks/Draft | PASS | GitHub odczytane dla a9e2fab |
| Preflight syntetyczny | PASS lokalnie | 9 testów + 11 istniejących cleanup, brak zmiany 17 tabel |
| Etapy 1–2 | PASS lokalnie z sesji 001 | nie powtarzano backup/restore bez zmiany ich kodu |
| Etap 3 release gate | READY przygotowanie / BLOCKED wykonanie | checklista/rollback/smoke/konta, brak kontroli produkcji i świeżej kopii |
| Etap 4 instrukcja Meta | READY | oficjalne źródła odczytane; rzeczywisty panel niezweryfikowany |
| Etapy 5–6 rzeczywiste Meta | BLOCKED | brak autoryzacji, konta testowego i zatwierdzonego scenariusza webhooków |
| Etap 7 | BLOCKED, nie rozpoczęty | osobna wyraźna zgoda wymagana |

Nie ma PASS production. Nie deklarujemy gotowości operacyjnej.

## Konkretne blokady i czynności właściciela

1. SQL: bieżąca polityka TCP środowiska ma puste domains/ip_ranges i vpn_configured=false.
   Nie wykonywano próby SSH ani zapytań produkcyjnych, nie obchodzono ograniczeń.
   Minimalny krok w Render: **Account settings → SSH Public Keys → + Add SSH Public Key**
   dla zatwierdzonego, bezpiecznie przechowywanego klucza. Osobno administrator środowiska
   musi dopuścić TCP ssh.frankfurt.render.com:22. Nie żądamy prywatnego klucza ani tokenu.
2. Po skonfigurowaniu kanału konieczna osobna zgoda na transfer/wykonanie narzędzia
   READ ONLY. Nie deployować aplikacji po to, żeby dostarczyć preflight.
   Historyczne 13 rekordów nie są aktualnym potwierdzeniem zakresu cleanup.
3. Świeżość/trwałość produkcyjnego backupu, klucza i undo niezweryfikowana;
   nie czytano prywatnych artefaktów. Wymagany zatwierdzony magazyn i test odtworzenia.
4. Meta: sprawdzić panel według OWNER_SETUP.md, dopiero po osobnym dopuszczeniu
   zmian/realnego testu. Nie aktywować OAuth/webhook/ingest/DM w tej sesji.
5. Osobne zgody pozostają wymagane dla merge/deploy/cleanup/zmian sekretów/Live/DM.

## Bezpieczeństwo i zakres zmian

Nie wykonano DML/COMMIT produkcji, migracji, merge, deploy ani aktywacji Meta.
Nie wysłano wiadomości i nie wykonano rzeczywistych wywołań Instagram/Graph/OAuth.
Nie zmieniano sekretów, allowlisty, sieci, płatnych zasobów ani konfiguracji produkcyjnej.
Nie otwierano historycznych archiwów/kopii ani .render-auth.
Ai Focus 1.0/2.0 nie zmieniono; wyłącznie pliki tego repozytorium Focus 3.0.
Diff względem main: diff-main.txt; lista plików sesji: git diff --name-only a9e2fab HEAD.

## Pozostałe sesje i wznowienie

**Pozostaje 5 sesji podstawowych + co najmniej 1 DM — licznik bez zmian.**
Przygotowanie zakończono lokalnie, ale żadnej z otwartych bramek operacyjnych nie zamknięto.
Nie obiecujemy stałej liczby sesji niezależnie od autoryzacji i zewnętrznych ograniczeń.

Kolejna sesja: odczytać HEAD i checks tej samej gałęzi/Draft PR #3, przeczytać najnowszy
komentarz właściciela oraz te dokumenty. Zachować Meta OFF i zakazy produkcyjne.
Bez nowej autoryzacji kontynuować wyłącznie niezależne zadania lokalne;
nie ponawiać testów zamkniętych bez zmiany kodu lub nowej przyczyny.
Testy PostgreSQL wyłącznie sekwencyjnie na focus3_test. Nie traktować tej sesji
jako zgody na wykonanie komend z OWNER_SETUP.md w produkcji.
Nie deklarujemy pracy w tle po zakończeniu sesji.
