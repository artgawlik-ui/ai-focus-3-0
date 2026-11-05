import httpx,pytest
from tests.e2e_discovery_transport import install


def test_synthetic_transport_cannot_escape_to_external_http(monkeypatch):
    monkeypatch.setenv('APP_ENV','test')
    monkeypatch.setenv('DATABASE_URL','postgresql://postgres@127.0.0.1/focus3_ci_synthetic')
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',httpx.HTTPTransport.handle_request)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,'handle_async_request',httpx.AsyncHTTPTransport.handle_async_request)
    install()
    assert httpx.get('https://nominatim.openstreetmap.org/search').json()[0]['lat']=='51.66'
    assert httpx.post('https://overpass-api.de/api/interpreter').json()['elements'][0]['tags']['name']=='[TEST] Salon promień'
    with pytest.raises(AssertionError):httpx.get('https://graph.facebook.com/v26.0/me')


@pytest.mark.parametrize('mode,database',[('production','focus3_ci_synthetic'),('test','focus3_production')])
def test_synthetic_transport_rejects_wrong_environment(monkeypatch,mode,database):
    monkeypatch.setenv('APP_ENV',mode)
    monkeypatch.setenv('DATABASE_URL','postgresql://postgres@127.0.0.1/'+database)
    with pytest.raises(RuntimeError):install()
