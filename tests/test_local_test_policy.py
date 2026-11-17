"""Dane wyłącznie syntetyczne; walidacja przed jakimkolwiek I/O."""
import pytest
from scripts.local_test_policy import local_origin, require_historical_artifact_consent

@pytest.mark.parametrize('origin', ['https://example.invalid', 'http://127.0.0.1.evil:8005', 'http://user:fixture@localhost:8005', 'http://localhost:8005?token=fixture', 'http://localhost:8005/#_', 'http://localhost', 'http://localhost:bad', 'file:///tmp/fixture'])
def test_nonlocal_or_ambiguous_origin_refused_without_echo(origin):
    with pytest.raises(ValueError) as error:
        local_origin(origin)
    assert origin not in str(error.value)

@pytest.mark.parametrize('origin', ['http://127.0.0.1:8005', 'http://localhost:8006/', 'http://[::1]:8005'])
def test_explicit_loopback_allowed(origin):
    assert local_origin(origin)==origin.rstrip('/')

def test_default_is_local_and_artifacts_require_separate_consent(monkeypatch):
    monkeypatch.delenv('FOCUS_TEST_ORIGIN', raising=False)
    monkeypatch.delenv('FOCUS_ALLOW_HISTORICAL_PRIVATE_ARTIFACTS', raising=False)
    assert local_origin()=='http://127.0.0.1:8005'
    with pytest.raises(SystemExit):
        require_historical_artifact_consent()
