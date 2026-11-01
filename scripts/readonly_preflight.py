"""Minimalny preflight bez importu aplikacji; stdout wyłącznie agregaty/statusy."""
import argparse,json,os,re
from urllib.parse import urlsplit
import psycopg
from scripts.salon_cleanup import ALL_TABLES,TABLES,inspection_sql,validate


def validate_destination(url, approved_internal=False):
    try:
        p=urlsplit(url.replace('postgresql+psycopg://','postgresql://'))
        local=p.hostname in ('localhost','127.0.0.1') and p.path=='/focus3_test'
        internal=approved_internal and bool(re.fullmatch(r'dpg-[a-z0-9-]+',p.hostname or '')) and p.path=='/ai_focus_3_0_db'
        if p.scheme!='postgresql' or p.query or p.fragment or not (local or internal):raise ValueError()
        _=p.port
    except Exception:raise ValueError('Nieautoryzowany cel preflightu') from None


def compare_scope(expected,actual):
    validate(expected)
    differences=[]
    for key in ('target_id','revision','schema_sha256','meta_links','active_jobs','salon_count'):
        if expected.get(key)!=actual.get(key):differences.append(key)
    for table in TABLES:
        if expected['tables'][table]!=actual.get('tables',{}).get(table):differences.append('table_'+table)
    counts={table:len(actual.get('tables',{}).get(table,{}).get('ids',[])) for table in TABLES}
    return {'status':'PASS' if not differences else 'BLOCKED','scope_matches':not differences,
            'differences':differences,'scope_counts':counts,'scope_total':sum(counts.values()),
            'schema_matches':expected['schema_sha256']==actual.get('schema_sha256')}


def run_preflight(url,manifest,approved_internal=False,technical_user_id=None,owner_user_id=None):
    validate_destination(url,approved_internal)
    validate(manifest)
    result=None
    connection=psycopg.connect(url.replace('postgresql+psycopg://','postgresql://'),autocommit=True,connect_timeout=5,
        options='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=10000 -c search_path=pg_catalog,public')
    try:
        connection.execute('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        try:
            actual=connection.execute(inspection_sql(manifest['target_id'])).fetchone()[0]
            result=compare_scope(manifest,actual)
            result['transaction_read_only']=connection.execute('SHOW transaction_read_only').fetchone()[0]=='on'
            result['isolation']=connection.execute('SHOW transaction_isolation').fetchone()[0]
            result['postgres_major']=connection.execute("SELECT current_setting('server_version_num')::integer/10000").fetchone()[0]
            result['public_table_count']=connection.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0]
            result['technical_account']='not_checked'
            result['owner_account']='not_checked'
            if technical_user_id is not None:
                row=connection.execute('SELECT active FROM public.users WHERE id=%s',(technical_user_id,)).fetchone()
                sessions=connection.execute('SELECT count(*) FROM public.sessions WHERE user_id=%s',(technical_user_id,)).fetchone()[0]
                result['technical_account']='PASS' if row is not None and row[0]==0 and sessions==0 else 'BLOCKED'
            if owner_user_id is not None:
                row=connection.execute('SELECT active,role FROM public.users WHERE id=%s',(owner_user_id,)).fetchone()
                result['owner_account']='PASS' if row is not None and row==(1,'manager') else 'BLOCKED'
            if not result['transaction_read_only'] or result['isolation']!='repeatable read' or result['public_table_count']!=len(ALL_TABLES) or result['postgres_major']!=17 or 'BLOCKED' in (result['technical_account'],result['owner_account']):result['status']='BLOCKED'
        finally:connection.execute('ROLLBACK')
    finally:connection.close()
    result.update({'dml_statements':0,'migrations_run':False,'application_started':False,'production_state_claimed':False})
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--approved-internal-readonly',action='store_true')
    parser.add_argument('--technical-user-id')
    parser.add_argument('--owner-user-id')
    args=parser.parse_args()
    try:
        with open(args.manifest) as source:manifest=json.load(source)
        result=run_preflight(os.environ['DATABASE_URL'],manifest,args.approved_internal_readonly,args.technical_user_id,args.owner_user_id)
    except Exception:
        result={'status':'BLOCKED','reason':'preflight_failed_no_details_exposed'}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
