"""Pure mocks: no database connection or provider requests."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import httpx
from backend.agent_provider import add_optional_questions
from backend.worker import authorized_salon


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv('AI_PAID_PROCESSING_APPROVED', 'true')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-provider-secret')
    post = Mock()
    monkeypatch.setattr(httpx, 'post', post)
    return post


@pytest.mark.parametrize('approved,key', [('false','x'), ('','x'), ('invalid','x'), ('true','')])
def test_provider_fail_closed(provider, monkeypatch, approved, key):
    monkeypatch.setenv('AI_PAID_PROCESSING_APPROVED', approved)
    monkeypatch.setenv('OPENAI_API_KEY', key)
    analysis = {'engine':'rules'}
    add_optional_questions(analysis,{})
    assert analysis == {'engine':'rules'}
    provider.assert_not_called()


@pytest.mark.parametrize('failure', [httpx.ReadTimeout('synthetic-provider-secret'), ValueError('synthetic-provider-secret')])
def test_provider_failure_preserves_analysis_and_redacts_logs(provider, failure, caplog):
    provider.side_effect = failure
    analysis = {'engine':'rules', 'draft':'synthetic draft', 'score':75}
    add_optional_questions(analysis,{})
    assert analysis == {'engine':'rules','draft':'synthetic draft','score':75,'model_status':'unavailable'}
    assert 'synthetic-provider-secret' not in caplog.text


@pytest.mark.parametrize('content', [None, '', 'x'*5001])
def test_bad_provider_content_falls_back(provider, content):
    provider.return_value.json.return_value = {'choices':[{'message':{'content':content}}]}
    analysis = {'engine':'rules'}
    add_optional_questions(analysis,{})
    assert analysis == {'engine':'rules','model_status':'unavailable'}


def test_provider_success_only_adds_unverified_questions(provider):
    provider.return_value.json.return_value = {'choices':[{'message':{'content':'Pytanie?'}}]}
    analysis = {'score':75}
    add_optional_questions(analysis,{'score':75})
    assert analysis['score']==75 and analysis['model_questions_unverified']=='Pytanie?'
    assert provider.call_args.kwargs['json']['store'] is False


@pytest.mark.parametrize('change', ['inactive','reassigned','missing','optout','blocked'])
def test_final_access_recheck_rejects_changes(change):
    db = Mock()
    user = SimpleNamespace(id='synthetic-user',active=True,role='sales')
    salon = SimpleNamespace(id='synthetic-salon',owner_id=user.id,status='prospect')
    db.get.side_effect = [user,salon]
    db.scalar.return_value = None
    job = SimpleNamespace(user_id=user.id,salon_id=salon.id)
    assert authorized_salon(db,job) is salon
    if change=='inactive':user.active=False
    if change=='reassigned':salon.owner_id='other-synthetic-user'
    if change=='blocked':salon.status='do_not_contact'
    if change=='optout':db.scalar.return_value='synthetic-optout'
    db.get.side_effect = [user,None if change=='missing' else salon]
    with pytest.raises(ValueError):authorized_salon(db,job,final=True)
    assert db.get.call_args.kwargs == {'populate_existing':True,'with_for_update':True}


@pytest.mark.parametrize('revoked', [False, True])
def test_worker_finalizes_only_after_second_access_check(monkeypatch, revoked):
    from backend import worker, qualification, meta
    db = Mock()
    db.__enter__ = Mock(return_value=db)
    db.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(worker, 'Session', lambda:db)
    job = SimpleNamespace(id='synthetic-job',user_id='synthetic-user',salon_id='synthetic-salon',evidence='',status='queued')
    salon = SimpleNamespace(id=job.salon_id,priority='B')
    db.scalar.return_value = job
    db.get.return_value = job
    db.execute.return_value.rowcount = 1
    db.scalars.return_value = []
    check = Mock(side_effect=[salon, ValueError('Access revoked') if revoked else salon])
    monkeypatch.setattr(worker,'authorized_salon',check)
    monkeypatch.setattr(meta,'agent_replies',lambda *_:[])
    monkeypatch.setattr(qualification,'analyze',lambda *_:{'engine':'rules','warning':''})
    monkeypatch.setattr(qualification,'minimal_model_context',lambda _: {})
    monkeypatch.setenv('AI_PAID_PROCESSING_APPROVED','false')
    assert worker.run_once()
    assert check.call_args.kwargs == {'final':True}
    assert job.status == ('failed' if revoked else 'completed')
    if revoked:db.add.assert_not_called()
    else:db.add.assert_called_once()
