from datetime import datetime,timezone
import pytest
from scripts.offsite_backup import signed_put,run_once

def test_s3_payload_and_date_are_authenticated():
    at=datetime(2026,10,28,tzinfo=timezone.utc)
    a=signed_put('https://storage.example/bucket/prefix/test.enc',b'encrypted-a','example-id','example-secret','eu-central-1',at)
    b=signed_put('https://storage.example/bucket/prefix/test.enc',b'encrypted-b','example-id','example-secret','eu-central-1',at)
    assert a['Authorization']!=b['Authorization']
    assert a['x-amz-date']=='20261028T000000Z'
    assert '20261028/eu-central-1/s3/aws4_request' in a['Authorization']

@pytest.mark.parametrize('url',['http://storage.example/a','https://user:secret@storage.example/a','https://storage.example/a?token=secret'])
def test_offsite_rejects_insecure_destinations(url):
    with pytest.raises(ValueError):signed_put(url,b'x','id','secret','eu-central-1')

def test_offsite_disabled_and_retention_required(monkeypatch):
    monkeypatch.delenv('OFFSITE_BACKUP_ENABLED',raising=False)
    assert run_once() is False
    monkeypatch.setenv('OFFSITE_BACKUP_ENABLED','true')
    monkeypatch.delenv('BACKUP_RETENTION_CONFIRMED_DAYS',raising=False)
    with pytest.raises(ValueError):run_once()
