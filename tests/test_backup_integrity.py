"""Uwierzytelnienie kopii aplikacji; brak cleanup, sieci i prawdziwej bazy."""
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from scripts.backup import derive,restore


@pytest.mark.parametrize('damage',['wrong_password','ciphertext','aad','truncated'])
def test_application_backup_rejects_corruption_before_pg_restore(tmp_path,monkeypatch,damage):
    import scripts.backup as module
    class EmptyTarget:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,*args):return self
        def fetchone(self):return (0,)
    monkeypatch.setattr(module.psycopg,'connect',lambda *a,**kw:EmptyTarget())
    def forbidden(*a,**kw):raise AssertionError('pg_restore must not receive unauthenticated data')
    monkeypatch.setattr(module.subprocess,'run',forbidden)
    phrase='synthetic-fixture-backup-passphrase'
    salt=b's'*16;nonce=b'n'*12
    aad=b'wrong-fixture-aad' if damage=='aad' else b'focus3-backup'
    encrypted=b'FOCUS3B1'+salt+nonce+AESGCM(derive(phrase,salt)).encrypt(nonce,b'fixture-not-a-database',aad)
    if damage=='ciphertext':encrypted=encrypted[:-1]+bytes([encrypted[-1]^1])
    if damage=='truncated':encrypted=encrypted[:40]
    path=tmp_path/'synthetic.enc';path.write_bytes(encrypted)
    monkeypatch.setenv('DATABASE_URL','postgresql://localhost/focus3_test')
    monkeypatch.setenv('RESTORE_DATABASE_URL','postgresql://localhost/focus3_synthetic_fixture')
    monkeypatch.setenv('BACKUP_PASSPHRASE','wrong-synthetic-passphrase' if damage=='wrong_password' else phrase)
    with pytest.raises(InvalidTag):restore(path)
