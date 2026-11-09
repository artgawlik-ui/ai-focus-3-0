# Zmiany sesji 001

- 9893b32: punkt zerowy i kryteria przed implementacją.
- ce1b480: guardy lokalne, testy odzyskiwania, preflight Meta, bramka integralności, CI.
- 45b436c: raport i agregaty dowodów.
- 5854732: klient pg_dump/pg_restore z istniejącego serwisu CI zamiast niedostępnego pakietu hosta.
- ccafa0c: uzupełnienie stanu wznowienia i zakresu zmian.
- Poprawka uruchamiania testu przeglądarkowego jako modułu: commit zawierający ten wpis (git log).
- Commit raportowy: odczytaj git log dla tego katalogu (plik nie zawiera własnego przyszłego SHA).

Pliki commitów przygotowania i implementacji względem zastanego 6eaed76:

- .github/workflows/tests.yml
- docs/sessions/session-001/ACCEPTANCE.md
- docs/sessions/session-001/START.md
- scripts/data_release_gate.py
- scripts/isolated_export_restore.py
- scripts/local_test_policy.py
- scripts/meta_local_preflight.py
- scripts/synthetic_export_probe.py
- tests/conftest.py
- tests/production_browser_check.py
- tests/production_check.py
- tests/production_integrity_check.py
- tests/production_meta_readonly_check.py
- tests/production_restore_check.py
- tests/test_data_release_gate.py
- tests/test_export_validation.py
- tests/test_local_test_policy.py
- tests/test_meta_local_preflight.py
- tests/test_synthetic_recovery.py

Dokumenty tej sesji: START.md, ACCEPTANCE.md, OPERATIONS.md, REPORT.md, evidence.json, synthetic-restore.json, CHANGES.md, diff-main.txt.
