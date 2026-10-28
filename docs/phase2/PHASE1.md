# Faza 1 — wynik 2026-10-28

Start: oficjalny Render list_deploys potwierdził live commit 0c44401d2b8ef2b7d11813e35aed69ab3b0de6fe. Konto techniczne nieaktywne, właściciel aktywny. Nowa kopia przed zmianą hasła zaszyfrowana i odtworzona tylko do pustej lokalnej bazy: zgodność liczebności i SHA-256 10 tabel. Hasło właściciela nie było zmieniane przez agenta. Właściciel potwierdził ręcznie instalację PWA i logowanie na fizycznym iPhonie; nie jest to test wykonany przez Codex.

Testy: `DATABASE_URL=<izolowana focus3_test> python -m pytest -q tests/test_api.py tests/test_offsite_backup.py`: 20 passed. `pip-audit -r requirements.txt` i `npm audit --prefix frontend`: 0 znanych podatności. Dwa ostrzeżenia deprecacji narzędzi testowych (httpx/TestClient i pytest/anyio), bez błędów testów; nie uznajemy ich za podatności.

Działa w kodzie: kontrola własności, historii mutacji, logowanie dostępu z identyfikatorem konta, trasą API, czasem i wynikiem bez treści/sekretów. Mechanizm hasła ma test starego hasła, hash Argon2id i wylogowanie innych sesji. MFA brak. Przygotowane: codzienny szyfrowany upload S3 i wymaganie retencji, wyłączone bez magazynu/kosztu; nie przetestowano realnego magazynu. Dokumentacja RODO wspiera administratora, nie stanowi deklaracji kompletnej zgodności prawnej.

Pliki: backend/main.py, backend/security.py, scripts/supervise.py, scripts/offsite_backup.py, tests/test_api.py, tests/test_offsite_backup.py, docs/phase2/BACKUPS.md, docs/phase2/PRIVACY.md, docs/phase2/PHASE1.md. Faza 1 nie zmienia schematu, nie usuwa klientów i nie aktywuje płatnych zasobów. Wdrożenie wspólne z fazą 2 dopiero po pełnych testach. Focus 1.0 i Focus 2.0 bez zmian.
