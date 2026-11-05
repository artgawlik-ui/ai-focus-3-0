# RAPORT AI FOCUS 3.0.4 — SESJA 010

## Wykonane

- Zweryfikowano lokalny commit 009: 9858db3177dd003e9463d55ec72eb8fd406287bb;
  początkowo GitHub był na 05a9e6b. Wykonano zwykły push, bez force/merge/deploy.
- PR #3 odczytany Draft. CI 009: 42081039659; backend/build success, ostatni odczyt
  E2E in progress. Końcowy wynik wymaga sprawdzenia; nie oznaczamy całej sesji PASS.
- Zinwentaryzowano zapis blokady: CRM status do_not_contact aktualizuje wiersz Salon;
  MetaConversation.opted_out zapisuje apply_payload; nowa relacja salon_id powstaje w bind.
  Worker sprawdza status i wszystkie powiązane rezygnacje. Zmiana CRM blokuje ten sam
  wiersz salonu co finalizacja workera. Dla opt-out i bind brakowało wspólnego zamka.
- Dodano lock_contact: pg_advisory_xact_lock z namespacem i hashem identyfikatora salonu.
  Worker pobiera go przed finalnymi blokadami user/salon; opt-out i bind przed zmianą
  stanu/powiązania. Commit/rollback zwalnia zamek. Kolizja hash tylko serializuje obce
  salony. SQLite nie jest dowodem tej synchronizacji (helper jest tam no-op).
- Worker nie blokuje rozmów; ścieżki Meta mogą blokować rozmowę przed advisory.
  Worker pobiera advisory przed user/salon, co pozwala uniknąć odwrócenia z blokadami
  FK wpisów historii w transakcji opt-out. Brak trzymania advisory w czasie HTTP modelu.
- Jeśli opt-out commit pierwszy: worker widzi blokadę i nie tworzy Activity/szkicu.
  Jeśli worker commit pierwszy: opt-out czeka i zatwierdza się później. Nie usuwa się
  historycznych szkiców; nowe zadania po blokadzie są odrzucane.

## Testy i ograniczenia dowodów

Lokalny Docker początkowo odrzucony przez sandbox; po dopuszczeniu lokalnego polecenia
potwierdzono daemon 28.4.0 i istniejący obraz postgres:17. Uruchomiono wyłącznie lokalną
syntetyczną bazę focus3_test na 127.0.0.1:55432, limit 256 MB / 1 CPU; żadnych kosztów Render.
Pierwszy test SQLite w sandboxie utknął po dwóch skipach i nie jest dowodem PASS.

`DATABASE_URL=postgresql://postgres@127.0.0.1:55432/focus3_test .venv/bin/python -m pytest -q tests/test_contact_concurrency.py tests/test_api.py tests/test_agent_resilience.py`
— **36 passed, 0 failed, 0 skipped, 12.34 s**.
3 nowe przypadki: oba porządki równoległych transakcji oraz rzeczywiste ścieżki bind/opt-out
potwierdzające użycie zamka. Dwie sesje/połączenia, bariery i kontrola oczekiwania zamiast
symulacji PostgreSQL. Pozostałe 33 to regresja API/CRM i agent resilience.
Ostrzeżenia: AnyIO CallSpec2 oraz Starlette/httpx deprecated; testy przechodzą.
Nie jest to test produkcyjnego obciążenia ani konta Meta. `git diff --check`: PASS.
Końcowy CI dokładnego HEAD pozostaje osobnym warunkiem; wynik w Checks/raporcie rozmowy.

## Rollout i rollback — wyłącznie plan

Brak nowego schematu. Cofnięcie kodu nie wymaga downgrade ani zmian danych.
**Stare workery nie stosują nowego zamka**: przed aktywacją ingestu muszą zakończyć pracę.
Meta OFF podczas całego przyszłego rollout; kontrolowany tryb workera i porównanie danych.
Nie wolno uznać gwarancji współbieżności za obowiązującą przy mieszance starych procesów.
Nie zmieniono flag, uprawnień, produkcji, danych klientów, sieci, sekretów ani Render.
Bez rzeczywistych DM, eksportów/restore, cleanup, migracji produkcji, merge i deploy.
Focus 1.0/2.0 nietknięte. PR ma pozostać Draft.

## BLOCKED / NEXT

Aktualny wewnętrzny SQL, konta/17 tabel/004, RPO ≤60 minut, trwały niezależny magazyn/klucz
oraz artefakt/env rollbacku nadal niepotwierdzone. Grant TCP pusty; brak prób SSH.
Zgoda A jest udzielona, nie pytać ponownie. Właściciel: zatwierdzić ograniczony grant TCP
Codex do ssh.frankfurt.render.com:22; nie zmieniać allowlisty PostgreSQL.
Następnie zweryfikować host/kanał/tożsamości i wykonać tylko 4 zatwierdzone SELECT-y.

Zmiany: backend/contact_guard.py, backend/worker.py, backend/meta.py,
backend/meta_inbox.py, tests/test_contact_concurrency.py, RESUME.md i dokumenty sesji 010.
SHA raportu: `git log -1 --format=%H -- docs/sessions/session-010/REPORT.md`.
**Status wydania BLOCKED. Pozostaje szacunkowo 5 sesji podstawowych + ≥1 DM**,
bez gwarantowanego terminu i bez obniżenia za same poprawki przy otwartych bramkach.
