import copy,json,pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from backend.main import app
from backend.meta_flags import feature,dm_enabled,send_dm
from scripts.meta_local_preflight import FLAGS
from scripts.release_dry_run import evaluate
from tests.test_api import clean,client,add


def profile():
    return {'source':'synthetic','version':'3.0.4','schema_revision':'004','flags':{k:'false' for k in FLAGS},
            'synthetic_restore_verified':True,'synthetic_rollback_verified':True,
            'synthetic_technical_disabled':True,'synthetic_owner_login_verified':True}


def test_offline_gate_does_not_authorize_production_or_echo_extra_fields():
    p=profile();p['private_fixture']='fixture-not-for-output'
    result=evaluate(p)
    assert result['status']=='PASS_LOCAL' and not result['production_verified']
    assert not any(result[k] for k in ('deployment_authorized','cleanup_authorized','meta_activation_authorized'))
    assert p['private_fixture'] not in json.dumps(result)
    for key in ('source','version','schema_revision','synthetic_restore_verified','synthetic_rollback_verified','synthetic_technical_disabled','synthetic_owner_login_verified'):
        bad=copy.deepcopy(p);bad.pop(key)
        assert evaluate(bad)['status']=='BLOCKED'


def test_every_flag_is_checked_independently_fail_closed():
    for name in FLAGS:
        for value in ('true','invalid','',True):
            bad=profile();bad['flags'][name]=value
            assert evaluate(bad)['status']=='BLOCKED'
    assert evaluate({**profile(),'flags':{}})['status']=='PASS_LOCAL'


def test_local_meta_off_crm_smoke_and_accounts(monkeypatch):
    for name in FLAGS:monkeypatch.setenv(name,'false')
    c=client();technical=client('rep1');salon=add(c,name='Synthetic release dry run')
    assert c.get('/api/health').json()=={'status':'ok','version':'3.0.4'}
    anonymous=TestClient(app)
    for path in ('/api/auth/me','/api/salons','/api/meta/status'):
        assert anonymous.get(path).status_code==401
    for path in ('/api/meta/oauth/callback','/api/meta/webhook'):
        assert anonymous.get(path).status_code==404
    assert c.post('/api/meta/oauth/start').status_code==404
    assert c.post('/api/meta/subscribe').status_code==404
    assert c.get('/api/salons/'+salon['id']).status_code==200
    assert all(not feature(name) for name in ('oauth','webhook_verify','ingest','crm_history','diagnostics'))
    assert not dm_enabled()
    with pytest.raises(HTTPException) as error:send_dm()
    assert error.value.status_code==403
    assert c.post('/api/users/rep1/deactivate').status_code==200
    assert technical.get('/api/auth/me').status_code==401
    assert c.get('/api/auth/me').status_code==200
    assert c.post('/api/auth/logout').status_code==200
    assert c.get('/api/auth/me').status_code==401
    assert client().get('/api/auth/me').status_code==200
