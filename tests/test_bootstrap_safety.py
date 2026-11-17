"""Bootstrap safety on the guarded synthetic test database; no real accounts."""
import os
import pytest
from sqlalchemy import select,func,delete
from backend.db import Session,User,LoginSession
from backend.security import ph
from scripts.bootstrap import main
from scripts.backup import fingerprint
from tests.test_api import clean

@pytest.mark.parametrize('legacy_secret',[None,'','short','SYNTHETIC_VERIFICATION_ONLY_123456789'])
def test_existing_accounts_are_unchanged_without_provisioning_password(monkeypatch,capsys,legacy_secret):
    monkeypatch.setenv('BOOTSTRAP_EMAIL','synthetic-replacement@focus.invalid')
    monkeypatch.delenv('BOOTSTRAP_PASSWORD',raising=False)
    if legacy_secret is None:monkeypatch.delenv('VERIFICATION_PASSWORD',raising=False)
    else:monkeypatch.setenv('VERIFICATION_PASSWORD',legacy_secret)
    with Session() as db:
        db.add(LoginSession(token_hash='synthetic-session-digest',user_id='manager',csrf='synthetic-csrf',expires='2099-01-01T00:00:00+00:00'));db.commit()
    before=fingerprint(os.environ['DATABASE_URL'])
    main()
    assert fingerprint(os.environ['DATABASE_URL'])==before
    with Session() as db:
        assert db.scalar(select(func.count()).select_from(User))==3
        assert db.scalar(select(func.count()).select_from(LoginSession))==1
        assert db.scalar(select(User).where(User.email=='verification@focus.invalid')) is None
    output=capsys.readouterr().out
    assert 'Bootstrap skipped' in output and 'synthetic-replacement' not in output
    assert not legacy_secret or legacy_secret not in output


def test_disabled_technical_account_is_not_reenabled_or_changed(monkeypatch,capsys):
    with Session() as db:
        db.add(User(id='synthetic-technical',email='verification@focus.invalid',name='Synthetic disabled',role='manager',active=0,password_hash='synthetic-disabled-hash'))
        db.commit()
    monkeypatch.setenv('VERIFICATION_PASSWORD','SYNTHETIC_VERIFICATION_ONLY_123456789')
    monkeypatch.delenv('BOOTSTRAP_EMAIL',raising=False);monkeypatch.delenv('BOOTSTRAP_PASSWORD',raising=False)
    before=fingerprint(os.environ['DATABASE_URL']);main()
    assert fingerprint(os.environ['DATABASE_URL'])==before
    with Session() as db:
        assert db.get(User,'synthetic-technical').active==0
        assert db.scalar(select(func.count()).select_from(LoginSession))==0
    assert 'SYNTHETIC' not in capsys.readouterr().out


def empty():
    with Session() as db:db.execute(delete(User));db.commit()


def test_empty_database_creates_only_initial_owner_and_is_idempotent(monkeypatch,capsys):
    empty();phrase='SyntheticInitialOwner123!'
    monkeypatch.setenv('BOOTSTRAP_EMAIL',' SYNTHETIC-OWNER@focus.invalid ')
    monkeypatch.setenv('BOOTSTRAP_PASSWORD',phrase)
    monkeypatch.setenv('VERIFICATION_PASSWORD','SYNTHETIC_VERIFICATION_ONLY_123456789')
    main()
    with Session() as db:
        users=list(db.scalars(select(User)));assert len(users)==1
        owner=users[0];assert owner.role=='manager' and owner.email=='synthetic-owner@focus.invalid'
        assert owner.password_hash.startswith('$argon2id$') and ph.verify(owner.password_hash,phrase)
    before=fingerprint(os.environ['DATABASE_URL']);main()
    assert fingerprint(os.environ['DATABASE_URL'])==before
    output=capsys.readouterr().out
    assert phrase not in output and 'SYNTHETIC_VERIFICATION_ONLY' not in output
    assert 'synthetic-owner@' not in output


@pytest.mark.parametrize('email,phrase',[('', 'SyntheticInitialOwner123!'),('synthetic@focus.invalid',''),('synthetic@focus.invalid','short'),('synthetic@focus.invalid','password123!'),('synthetic@focus.invalid','x'*12),('synthetic@focus.invalid','x'*201),('x'*255,'SyntheticInitialOwner123!')])
def test_empty_database_rejects_missing_or_short_provisioning_credentials(monkeypatch,capsys,email,phrase):
    empty();monkeypatch.setenv('BOOTSTRAP_EMAIL',email);monkeypatch.setenv('BOOTSTRAP_PASSWORD',phrase)
    monkeypatch.setenv('VERIFICATION_PASSWORD','SYNTHETIC_VERIFICATION_ONLY_123456789')
    with pytest.raises(SystemExit) as result:main()
    assert 'Set BOOTSTRAP_EMAIL and BOOTSTRAP_PASSWORD' in str(result.value)
    import traceback
    rendered=''.join(traceback.format_exception(result.type,result.value,result.tb))
    assert not phrase or phrase not in str(result.value)
    if len(phrase)>20:assert phrase not in rendered
    with Session() as db:assert db.scalar(select(func.count()).select_from(User))==0
    assert not capsys.readouterr().out


def test_failed_transaction_does_not_log_secret_or_leave_partial_account(monkeypatch,capsys):
    from sqlalchemy import event
    from scripts import bootstrap
    import traceback
    empty();sentinel='SYNTHETIC_PRIVATE_DRIVER_DETAIL'
    monkeypatch.setenv('BOOTSTRAP_EMAIL','synthetic-owner@focus.invalid')
    monkeypatch.setenv('BOOTSTRAP_PASSWORD','SyntheticInitialOwner123!')
    original=Session
    def fail():
        session=original()
        def before_commit(_):raise RuntimeError(sentinel)
        event.listen(session,'before_commit',before_commit)
        return session
    monkeypatch.setattr(bootstrap,'Session',fail)
    before=fingerprint(os.environ['DATABASE_URL'])
    with pytest.raises(SystemExit) as result:main()
    assert 'Bootstrap failed' in str(result.value)
    assert sentinel not in ''.join(traceback.format_exception(result.type,result.value,result.tb))
    assert fingerprint(os.environ['DATABASE_URL'])==before
    with original() as db:assert db.scalar(select(func.count()).select_from(User))==0
    output=capsys.readouterr();assert not output.out and not output.err


@pytest.mark.parametrize('isolation',['READ COMMITTED','REPEATABLE READ'])
def test_two_empty_database_bootstrappers_create_one_owner(monkeypatch,capsys,isolation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event,Lock
    from sqlalchemy import event
    from sqlalchemy.orm import sessionmaker
    from backend.db import engine
    from scripts import bootstrap
    empty();monkeypatch.setenv('BOOTSTRAP_EMAIL','synthetic-owner@focus.invalid')
    monkeypatch.setenv('BOOTSTRAP_PASSWORD','SyntheticInitialOwner123!')
    monkeypatch.setenv('VERIFICATION_PASSWORD','SYNTHETIC_VERIFICATION_ONLY_123456789')
    monkeypatch.setattr(bootstrap,'Session',sessionmaker(engine.execution_options(isolation_level=isolation)))
    entered=Event();release=Event();both_locks=Event();attempts=[];hashed=[];guard=Lock()
    original_hash=ph.hash
    def hash_once(value):
        with guard:hashed.append(1)
        entered.set();assert release.wait(10)
        return original_hash(value)
    def observe(conn,cursor,statement,*args):
        if 'pg_advisory_xact_lock' in statement:
            attempts.append(1)
            if len(attempts)==2:both_locks.set()
    from types import SimpleNamespace
    monkeypatch.setattr(bootstrap,'ph',SimpleNamespace(hash=hash_once))
    event.listen(engine,'before_cursor_execute',observe)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(main);second=None
            try:
                assert entered.wait(5)
                second=pool.submit(main)
                assert both_locks.wait(5)
            finally:release.set()
            assert first.result(timeout=10) is None
            if second:assert second.result(timeout=10) is None
    finally:event.remove(engine,'before_cursor_execute',observe);release.set()
    with Session() as db:assert db.scalar(select(func.count()).select_from(User))==1
    assert len(hashed)==1
    assert 'SYNTHETIC' not in capsys.readouterr().out
