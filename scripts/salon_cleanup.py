"""Przygotowanie planu i SQL. Brak połączeń, transportu i funkcji wykonującej COMMIT."""
import json,re,uuid

TABLES=('activities','appointments','jobs','integration_links','salons')
ALL_TABLES=('activities','alembic_version','appointments','integration_links','jobs','login_attempts','meta_conversations','meta_credentials','meta_messages','meta_oauth_states','meta_privacy_requests','meta_refresh_states','meta_webhook_inbox','salons','sessions','trainings','users')

class CleanupError(ValueError):pass

def ident(value):
    if not isinstance(value,str) or str(uuid.UUID(value))!=value:raise CleanupError('invalid_identifier')
    return value

def literal(value):return "'"+value.replace("'","''")+"'"

def scope(table,target):return 'id='+literal(target) if table=='salons' else 'salon_id='+literal(target)

def digest(table,where='true'):
    if table not in ALL_TABLES:raise CleanupError('unknown_table')
    return "(SELECT encode(sha256(convert_to(coalesce(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text COLLATE \"C\"),''),'UTF8')),'hex') FROM public."+table+' t WHERE '+where+')'

SCHEMA_SQL="""(SELECT encode(sha256(convert_to(jsonb_build_object(
 'tables',(SELECT jsonb_agg(jsonb_build_array(c.relname,c.relkind,c.relrowsecurity,c.relforcerowsecurity) ORDER BY c.relname COLLATE "C") FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p')),
 'columns',(SELECT jsonb_agg(jsonb_build_array(c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,pg_get_expr(d.adbin,d.adrelid)) ORDER BY c.relname COLLATE "C",a.attnum) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname='public' AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped),
 'indexes',(SELECT jsonb_agg(jsonb_build_array(t.relname,c.relname,pg_get_indexdef(i.indexrelid)) ORDER BY t.relname COLLATE "C",c.relname COLLATE "C") FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public'),
 'constraints',(SELECT jsonb_agg(jsonb_build_array(n.nspname,c.relname,k.conname,pg_get_constraintdef(k.oid),k.convalidated) ORDER BY c.relname COLLATE "C",k.conname COLLATE "C") FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' OR k.confrelid IN (SELECT t.oid FROM pg_class t JOIN pg_namespace s ON s.oid=t.relnamespace WHERE s.nspname='public' AND t.relname IN ('salons','activities','appointments','jobs','integration_links')))
)::text,'UTF8')),'hex'))"""


def inspection_sql(target):
    target=ident(target);parts=[]
    for table in TABLES:
        where=scope(table,target)
        parts.extend([literal(table),"jsonb_build_object('ids',(SELECT coalesce(jsonb_agg(id ORDER BY id),'[]') FROM public."+table+' WHERE '+where+"),'sha256',"+digest(table,where)+')'])
    return "SELECT jsonb_build_object('target_id',"+literal(target)+",'revision',(SELECT version_num FROM public.alembic_version),'schema_sha256',"+SCHEMA_SQL+",'tables',jsonb_build_object("+','.join(parts)+"),'meta_links',(SELECT count(*) FROM public.meta_conversations WHERE salon_id="+literal(target)+"),'active_jobs',(SELECT count(*) FROM public.jobs WHERE salon_id="+literal(target)+" AND status IN ('queued','running')),'salon_count',(SELECT count(*) FROM public.salons));"


def validate(plan):
    target=ident(plan['target_id'])
    if plan.get('original_target_id')!=target or plan.get('owner_confirmed_original_test') is not True or plan.get('fresh_backup_verified') is not True:raise CleanupError('identity_or_backup_unconfirmed')
    if plan.get('revision')!='004' or plan.get('meta_links')!=0 or plan.get('active_jobs')!=0:raise CleanupError('unsafe_dependencies')
    for key in ('schema_sha256','backup_sha256'):
        if not re.fullmatch('[a-f0-9]{64}',plan.get(key,'')):raise CleanupError('invalid_fingerprint')
    if set(plan['tables'])!=set(TABLES):raise CleanupError('unexpected_scope')
    for table,data in plan['tables'].items():
        if not re.fullmatch('[a-f0-9]{64}',data.get('sha256','')):raise CleanupError('invalid_fingerprint')
        ids=data['ids']
        if not isinstance(ids,list) or sorted(set(ids))!=ids:raise CleanupError('invalid_id_set')
        for id in ids:ident(id)
    if plan['tables']['salons']['ids']!=[target]:raise CleanupError('ambiguous_target')
    return target


def survivors(target):
    parts=[]
    for table in ALL_TABLES:
        where='NOT ('+scope(table,target)+')' if table in TABLES else 'true'
        parts.extend([literal(table),digest(table,where)])
    return 'jsonb_build_object('+','.join(parts)+')'


def guard_header(plan,database):
    target=validate(plan)
    if database not in ('ai_focus_3_0_db','focus3_test','restored'):raise CleanupError('database_not_allowed')
    affected=','.join('public.'+x for x in TABLES+('meta_conversations',))
    return [
        '-- Plan wyłącznie do przeglądu i próby ROLLBACK. COMMIT wymaga osobnej zgody.',
        '-- Backup SHA-256: '+plan['backup_sha256'],
        'BEGIN ISOLATION LEVEL SERIALIZABLE;',
        "SET LOCAL search_path=pg_catalog,public; SET LOCAL standard_conforming_strings=on;",
        "SET LOCAL lock_timeout='2s'; SET LOCAL statement_timeout='10s'; SET LOCAL idle_in_transaction_session_timeout='15s';",
        'LOCK TABLE '+affected+' IN SHARE ROW EXCLUSIVE MODE;',
        'DO $cleanup$ DECLARE n bigint; unchanged jsonb; BEGIN',
        'IF current_database()<>'+literal(database)+" THEN RAISE EXCEPTION 'Wrong database'; END IF;",
        "IF current_setting('server_version_num')::integer/10000<>17 THEN RAISE EXCEPTION 'Wrong PostgreSQL major'; END IF;",
        "IF (SELECT version_num FROM public.alembic_version)<>'004' THEN RAISE EXCEPTION 'Wrong revision'; END IF;",
        'IF '+SCHEMA_SQL+'<>'+literal(plan['schema_sha256'])+" THEN RAISE EXCEPTION 'Schema changed'; END IF;",
        "IF EXISTS(SELECT 1 FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN ("+','.join(literal('public.'+x)+'::regclass' for x in TABLES)+")) OR EXISTS(SELECT 1 FROM pg_rewrite WHERE ev_class IN ("+','.join(literal('public.'+x)+'::regclass' for x in TABLES)+")) THEN RAISE EXCEPTION 'Custom triggers or rules'; END IF;",
        "IF EXISTS(SELECT 1 FROM pg_class WHERE oid IN ("+','.join(literal('public.'+x)+'::regclass' for x in TABLES)+") AND (relrowsecurity OR relforcerowsecurity)) THEN RAISE EXCEPTION 'RLS enabled'; END IF;",
        "IF EXISTS(SELECT 1 FROM public.meta_conversations WHERE salon_id="+literal(target)+") THEN RAISE EXCEPTION 'Meta link needs separate review'; END IF;",
        "IF EXISTS(SELECT 1 FROM pg_constraint WHERE contype='f' AND confrelid IN ("+','.join(literal('public.'+x)+'::regclass' for x in TABLES)+") AND (confdeltype NOT IN ('a','r') OR confrelid<>'public.salons'::regclass OR conrelid NOT IN ("+','.join(literal('public.'+x)+'::regclass' for x in TABLES[:-1]+('meta_conversations',))+"))) THEN RAISE EXCEPTION 'Unexpected incoming foreign key'; END IF;",
        'unchanged := '+survivors(target)+';'
    ]


def build_delete_sql(plan,database='ai_focus_3_0_db'):
    target=validate(plan);lines=guard_header(plan,database)
    for table in TABLES:
        data=plan['tables'][table];where=scope(table,target)
        array='ARRAY['+','.join(literal(x) for x in data['ids'])+']::text[]'
        lines.append("IF (SELECT coalesce(array_agg(id::text ORDER BY id),ARRAY[]::text[]) FROM public."+table+' WHERE '+where+')<>'+array+' OR '+digest(table,where)+'<>'+literal(data['sha256'])+" THEN RAISE EXCEPTION 'Scope changed: "+table+"'; END IF;")
    lines.append("IF EXISTS(SELECT 1 FROM public.jobs WHERE salon_id="+literal(target)+" AND status IN ('queued','running')) THEN RAISE EXCEPTION 'Agent job in progress'; END IF;")
    for table in TABLES:
        data=plan['tables'][table];array='ARRAY['+','.join(literal(x) for x in data['ids'])+']::text[]'
        lines.append('DELETE FROM public.'+table+' WHERE '+scope(table,target)+' AND id::text=ANY('+array+');')
        lines.append("GET DIAGNOSTICS n=ROW_COUNT; IF n<>"+str(len(data['ids']))+" THEN RAISE EXCEPTION 'Unexpected delete count'; END IF;")
        lines.append('IF EXISTS(SELECT 1 FROM public.'+table+' WHERE '+scope(table,target)+") THEN RAISE EXCEPTION 'Target rows remain'; END IF;")
    lines+=['IF unchanged IS DISTINCT FROM '+survivors(target)+" THEN RAISE EXCEPTION 'Unrelated data changed'; END IF;",'END $cleanup$;','ROLLBACK;']
    return '\n'.join(lines)+'\n'


def build_restore_sql(plan,rows,database='ai_focus_3_0_db'):
    """Wynik może zawierać dane; przechowywać wyłącznie zaszyfrowany, nigdy w repo."""
    target=validate(plan)
    if set(rows)!=set(TABLES):raise CleanupError('unexpected_scope')
    for table,data in rows.items():
        if sorted(x['id'] for x in data)!=plan['tables'][table]['ids']:raise CleanupError('restore_id_mismatch')
        if table!='salons' and any(x['salon_id']!=target for x in data):raise CleanupError('restore_scope_mismatch')
    lines=guard_header(plan,database)
    for table in TABLES:
        ids='ARRAY['+','.join(literal(x) for x in plan['tables'][table]['ids'])+']::text[]'
        lines.append('IF EXISTS(SELECT 1 FROM public.'+table+' WHERE id::text=ANY('+ids+') OR '+scope(table,target)+") THEN RAISE EXCEPTION 'Restore collision'; END IF;")
    for table in ('salons','activities','appointments','jobs','integration_links'):
        payload=literal(json.dumps(rows[table],ensure_ascii=False,separators=(',',':')))
        lines.append('INSERT INTO public.'+table+' SELECT * FROM jsonb_populate_recordset(NULL::public.'+table+','+payload+'::jsonb);')
        lines.append('IF '+digest(table,scope(table,target))+'<>'+literal(plan['tables'][table]['sha256'])+" THEN RAISE EXCEPTION 'Restored row mismatch'; END IF;")
    lines+=['IF unchanged IS DISTINCT FROM '+survivors(target)+" THEN RAISE EXCEPTION 'Unrelated data changed'; END IF;",'END $cleanup$;','ROLLBACK;']
    return '\n'.join(lines)+'\n'
