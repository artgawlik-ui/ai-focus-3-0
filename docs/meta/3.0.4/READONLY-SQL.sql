-- Plan kontroli przez uprawniony dostęp wewnętrzny. Nie uruchomiono na produkcji.
-- Bez DDL/DML i bez wyświetlania treści, identyfikatorów klientów oraz tokenów.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '3000ms';
SHOW transaction_read_only;
SELECT version_num FROM alembic_version; -- oczekiwane 004
SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;
SELECT state, count(*) FROM pg_stat_activity WHERE datname=current_database() GROUP BY state;
SELECT pg_database_size(current_database()) AS database_bytes;
SELECT status,dead_letter,count(*),min(created_at) AS oldest
  FROM meta_webhook_inbox GROUP BY status,dead_letter;
SELECT count(*) FILTER(WHERE revoked=0) AS active_grants,
       count(*) FILTER(WHERE revoked=0 AND token_ciphertext='') AS missing_ciphertext
  FROM meta_credentials;
SELECT status,count(*) FROM meta_refresh_states GROUP BY status;
SELECT indexname,indexdef FROM pg_indexes
  WHERE schemaname='public' AND tablename IN ('meta_webhook_inbox','meta_messages','meta_conversations');
SELECT count(*) AS active_technical_accounts FROM users
  WHERE email='verification@focus.invalid' AND active=1; -- oczekiwane 0
SELECT count(*) AS active_technical_sessions FROM sessions s JOIN users u ON u.id=s.user_id
  WHERE u.email='verification@focus.invalid' AND s.expires > CURRENT_TIMESTAMP::text;
ROLLBACK;
-- Dokładne liczby + SHA-256 wszystkich tabel: scripts.backup.fingerprint(...,
-- include_metadata=True), wyłącznie przez zatwierdzony kanał odczytu, bez wypisywania URL.
-- Helper korzysta z transakcji REPEATABLE READ READ ONLY i zwraca tylko count/hash.
