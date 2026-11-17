"""Cztery stałe zapytania SELECT; brak połączeń, aplikacji i funkcji wykonujących SQL."""
TABLES=('activities','alembic_version','appointments','integration_links','jobs','login_attempts','meta_conversations','meta_credentials','meta_messages','meta_oauth_states','meta_privacy_requests','meta_refresh_states','meta_webhook_inbox','salons','sessions','trainings','users')


def queries():
    expected=','.join("'"+name+"'" for name in TABLES)
    baseline="""SELECT current_setting('transaction_read_only')='on' AS read_only,
 current_setting('transaction_isolation')='repeatable read' AS repeatable_read,
 current_setting('server_version_num')::integer/10000 AS postgres_major,
 (SELECT array_agg(version_num ORDER BY version_num) FROM public.alembic_version) AS revisions,
 (SELECT count(*) FROM pg_tables WHERE schemaname='public') AS public_table_count,
 NOT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename NOT IN ("""+expected+""")) AS no_unknown_tables,
 NOT EXISTS(SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public' AND NOT c.convalidated) AS constraints_validated"""
    accounts="""SELECT
 %(owner_user_id)s::text IS NOT NULL AND %(technical_user_id)s::text IS NOT NULL AND %(owner_user_id)s::text<>%(technical_user_id)s::text AS distinct_approved_accounts,
 EXISTS(SELECT 1 FROM public.users WHERE id=%(owner_user_id)s::text AND active=1 AND role='manager') AS owner_active_manager,
 EXISTS(SELECT 1 FROM public.users WHERE id=%(technical_user_id)s::text AND active=0) AS technical_disabled,
 (SELECT count(*) FROM public.sessions WHERE user_id=%(technical_user_id)s::text) AS technical_sessions_total,
 (SELECT count(*) FROM public.sessions WHERE user_id=%(technical_user_id)s::text AND expires::timestamptz>CURRENT_TIMESTAMP) AS technical_sessions_valid"""
    parts=[]
    for table in TABLES:
        parts.append("SELECT '"+table+"' AS table_name,count(*) AS row_count,encode(sha256(convert_to(coalesce(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text COLLATE \"C\"),''),'UTF8')),'hex') AS sha256 FROM public.\""+table+'" t')
    fingerprints='SELECT * FROM ('+' UNION ALL '.join(parts)+') fingerprints ORDER BY table_name'
    worker="""SELECT
 (SELECT count(*) FROM public.jobs WHERE status='queued') AS queued_jobs,
 (SELECT count(*) FROM public.jobs WHERE status='running') AS running_jobs,
 (SELECT count(*) FROM public.meta_webhook_inbox WHERE status IN ('pending','processing')) AS inbox_open,
 (SELECT count(*) FROM public.meta_webhook_inbox WHERE status='failed' OR dead_letter=1) AS inbox_failed,
 (SELECT count(*) FROM public.meta_webhook_inbox WHERE status='done' AND payload_ciphertext<>'' AND NULLIF(processed_at,'')::timestamptz<CURRENT_TIMESTAMP-interval '7 days') AS inbox_payloads_retention_due,
 (SELECT count(*) FROM public.meta_webhook_inbox WHERE status='done' AND NULLIF(processed_at,'')::timestamptz<CURRENT_TIMESTAMP-interval '90 days') AS inbox_rows_retention_due,
 (SELECT count(*) FROM public.meta_messages WHERE body_ciphertext<>'' AND NULLIF(occurred_at,'')::timestamptz<CURRENT_TIMESTAMP-interval '30 days') AS message_content_retention_due,
 (SELECT count(*) FROM public.meta_messages WHERE NULLIF(occurred_at,'')::timestamptz<CURRENT_TIMESTAMP-interval '90 days') AS message_rows_retention_due,
 (SELECT count(*) FROM public.meta_oauth_states WHERE NULLIF(expires_at,'')::timestamptz<CURRENT_TIMESTAMP) AS oauth_states_retention_due,
 (SELECT count(*) FROM public.meta_webhook_inbox WHERE status='done' AND processed_at='') + (SELECT count(*) FROM public.meta_messages WHERE occurred_at='') + (SELECT count(*) FROM public.meta_oauth_states WHERE expires_at='') AS missing_retention_timestamps"""
    return {'baseline':baseline,'accounts':accounts,'fingerprints':fingerprints,'worker':worker}


def render_sql(psql=False):
    bundle="-- Nie wykonano na produkcji. Parametry kont przekazuje prywatnie zatwierdzony operator.\nBEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\nSET LOCAL TIME ZONE 'UTC';\nSET LOCAL search_path=pg_catalog,public;\nSET LOCAL statement_timeout='5s';\nSET LOCAL lock_timeout='1s';\nSET LOCAL idle_in_transaction_session_timeout='10s';\n\n"+'\n\n'.join('-- '+name+'\n'+query+';' for name,query in queries().items())+'\n\nROLLBACK;\n'
    if psql:
        bundle=bundle.replace('%(owner_user_id)s',":'owner_user_id'").replace('%(technical_user_id)s',":'technical_user_id'")
        bundle="\\set ON_ERROR_STOP on\n\\set ECHO none\n\\prompt 'Approved owner ID: ' owner_user_id\n\\prompt 'Approved technical ID: ' technical_user_id\n"+bundle
    return bundle

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--psql',action='store_true');args=parser.parse_args()
    print(render_sql(args.psql),end='')
