# RAPORT AI FOCUS 3.0.4 — SESJA 009

## DONE

Punkt wejściowy 05a9e6be77b6993d942a9b4cc76398527b403298; gałąź robocza zachowana.
Przeczytano RESUME, raport 008, dokumentację zgody 007 i RELEASE_GATE.
CI wejściowe 42077691424 w trakcie: backend i build success; instalacja przeglądarek
jeszcze trwała w odczycie. Nie przypisujemy temu SHA historycznego PASS innego commita.
Trzech nieśledzonych archiwów nie otwierano i nie publikowano.

1. Opcjonalny model: wyodrębniono backend/agent_provider.py. Timeout, błąd HTTP/JSON
   lub niepoprawne pytania nie niszczą analizy regułowej. Wynik ma model_status=unavailable,
   bez przejęcia decyzji przez model. Nadal wymagane oba warunki: zgoda płatnego AI i klucz.
   Nie aktywowano żadnego dostawcy. Nie dodano retry generujących dodatkowe koszty.
2. Worker: uprawnienia i blokadę kontaktu sprawdza przed analizą i ponownie po niej.
   Finalny odczyt wymusza odświeżenie identity map ORM i blokuje wiersze użytkownika oraz
   salonu do zapisu. Zmiana właściciela, dezaktywacja, brak salonu lub opt-out odrzuca szkic.
   Nie gwarantuje to serializacji równoległej zmiany opt-out w MetaConversation:
   tam istnieje osobna transakcja; testy nie stanowią dowodu pełnej współbieżności PostgreSQL.
3. Dodano 17 testów na mockach: flagi fail-closed, awarie, treść odpowiedzi, bezpieczne
   logi, ponowne RBAC i pełna ścieżka workera z odmową zapisu Activity po utracie dostępu.

## Dowody testowe

`.venv/bin/python -m pytest -q tests/test_agent_resilience.py tests/test_supervise.py tests/test_offsite_backup.py tests/test_data_release_gate.py`
— **29 passed, 0 failed, 0 skipped** (17 nowych + 12 wcześniejszych).
Nie tworzono bazy, nie wykonywano SQL, HTTP ani rzeczywistych procesów potomnych.
Ostrzeżenie środowiskowe AnyIO/pytest CallSpec2 pozostaje; nie blokuje testów.
`git diff --check` PASS. Nie zmieniono zależności, modeli ani migracji.
Końcowy standardowy CI po push: wynik przypisany do SHA w Checks PR #3 i końcowym
raporcie rozmowy; syntetyczny runner PostgreSQL, nie baza Render ani kopia klientów.
Nie wykonywano lokalnie ponownego restore lub zakończonej pełnej regresji.

## BLOCKED / IN PROGRESS

- Brak grantu TCP (odczyt polityki: domains=[], ip_ranges=[], VPN=false). 0 prób SSH,
  0 SELECT-ów. Zgoda A aktualna, lecz kanał i prywatne tożsamości niepotwierdzone.
- RPO 60 minut, aktualne 004/konta/hash danych, trwały niezależny magazyn/klucz,
  dostępność artefaktu/env rollbacku i rozliczenie zapisów podczas rollout nadal otwarte.
- Realny Meta OAuth/webhook niezweryfikowany; mocki nie są testem konta Instagram.
- W sesji 008 aktualizacja opisu PR przez gh pr edit nie powiodła się (deprecated
  projectCards w GraphQL); próba REST została przerwana. W 009 użyć ograniczonego czasowo
  REST, nie ponawiać wiszącego narzędzia MCP. Push aktualizuje zawartość PR niezależnie.

## NEXT

Grant TCP Codex do ssh.frankfurt.render.com:22 pozostaje jedną czynnością odblokowującą
kontrolę SQL; nie otwierać allowlisty. Potem zweryfikować host i istniejącą autoryzację,
prywatne tożsamości i wykonać dokładnie zatwierdzone cztery SELECT-y.
Niezależnie sprawdzić CI końcowego SHA; dalsze prace nad współbieżnością worker/opt-out
na syntetycznym środowisku testowym, bez włączania integracji.

Pliki: backend/agent_provider.py, backend/worker.py, tests/test_agent_resilience.py,
RESUME.md, docs/sessions/session-009/ACCEPTANCE.md, REPORT.md.
Commit raportu: `git log -1 --format=%H -- docs/sessions/session-009/REPORT.md`.
Bez zmian produkcji, klientów, Render/Meta/sieci/sekretów; brak DELETE/cleanup,
produkcyjnych migracji, eksportów/restore, merge/deploy, kosztów i rzeczywistych DM.
Focus 1.0/2.0 nietknięte. PR pozostaje Draft.
**Wydanie BLOCKED. Szacunek: 5 sesji podstawowych + ≥1 DM**; bez redukcji za same poprawki
przy otwartych bramkach operacyjnych, bez gwarantowanego terminu.
