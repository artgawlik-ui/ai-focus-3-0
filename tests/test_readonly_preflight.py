"""Każda baza i każdy rekord syntetyczny, testy sekwencyjne."""
import copy,json,pytest
from backend.db import engine
from scripts.readonly_preflight import validate_destination,compare_scope,run_preflight
from scripts.backup import fingerprint
from tests.test_salon_cleanup import clean,prepare,connect


def test_real_local_readonly_transaction_preserves_all_tables():
    plan,_,_=prepare()
    url=engine.url.render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    with connect() as db:db.execute("UPDATE users SET active=0 WHERE id='rep1'");db.commit()
    before=fingerprint(url,True)
    result=run_preflight(url,plan,technical_user_id='rep1',owner_user_id='manager')
    assert result['status']=='PASS' and result['transaction_read_only'] and result['isolation']=='repeatable read'
    assert result['public_table_count']==17 and result['technical_account']=='PASS' and result['owner_account']=='PASS'
    assert fingerprint(url,True)==before and result['dml_statements']==0
    output=json.dumps(result)
    assert plan['target_id'] not in output and plan['schema_sha256'] not in output and 'rep1' not in output
    for table in plan['tables']:
        for identifier in plan['tables'][table]['ids']:assert identifier not in output


def test_scope_drift_and_unsafe_accounts_fail_closed():
    plan,_,_=prepare()
    for key in ('revision','schema_sha256','meta_links','active_jobs','salon_count','target_id'):
        changed=copy.deepcopy(plan);changed[key]='synthetic-drift'
        assert compare_scope(plan,changed)['status']=='BLOCKED'
    for table in plan['tables']:
        changed=copy.deepcopy(plan);changed['tables'][table]['sha256']='f'*64
        assert compare_scope(plan,changed)['status']=='BLOCKED'
        changed=copy.deepcopy(plan);changed['tables'][table]['ids'].append('synthetic-drift')
        assert compare_scope(plan,changed)['status']=='BLOCKED'
    url=engine.url.render_as_string(hide_password=False).replace('postgresql+psycopg://','postgresql://')
    assert run_preflight(url,plan,technical_user_id='rep1',owner_user_id='missing')['status']=='BLOCKED'


@pytest.mark.parametrize('url', ['postgresql://localhost/other','postgresql://example.invalid/focus3_test','postgresql://dpg-example-a/ai_focus_3_0_db','postgresql://localhost/focus3_test?options=fixture','postgresql://localhost/focus3_test#fragment'])
def test_no_remote_connection_without_explicit_approval(url):
    with pytest.raises(ValueError) as error:validate_destination(url)
    assert url not in str(error.value)


def test_internal_gate_does_not_allow_public_database_host():
    validate_destination('postgresql://dpg-synthetic-a/ai_focus_3_0_db',True)
    with pytest.raises(ValueError):validate_destination('postgresql://dpg-synthetic-a.frankfurt-postgres.render.com/ai_focus_3_0_db',True)


def test_cli_refuses_external_url_without_echoing_secrets(tmp_path):
    import os,subprocess,sys
    plan,_,_=prepare();path=tmp_path/'synthetic.json';path.write_text(json.dumps(plan))
    result=subprocess.run([sys.executable,'-m','scripts.readonly_preflight','--manifest',str(path)],env={**os.environ,'DATABASE_URL':'postgresql://fixture-user:fixture-private@example.invalid/focus3_test'},capture_output=True,text=True)
    output=json.loads(result.stdout)
    assert result.returncode==1 and output['status']=='BLOCKED' and not result.stderr
    assert 'fixture-private' not in result.stdout and 'fixture-user' not in result.stdout
