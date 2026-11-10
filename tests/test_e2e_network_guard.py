import json,socket
import httpx,pytest
from tests.e2e_network_guard import install,self_probe
from tests.e2e_discovery_transport import install as fixtures

@pytest.fixture
def guard(monkeypatch,tmp_path):
    monkeypatch.setenv('APP_ENV','test');monkeypatch.setenv('DATABASE_URL','postgresql://postgres@127.0.0.1/focus3_ci_guard')
    path=tmp_path/'attempts.jsonl';monkeypatch.setenv('FOCUS_TEST_EXTERNAL_ATTEMPTS',str(path))
    for name in ('connect','connect_ex'):monkeypatch.setattr(socket.socket,name,getattr(socket.socket,name))
    monkeypatch.setattr(socket,'getaddrinfo',socket.getaddrinfo)
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',httpx.HTTPTransport.handle_request)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,'handle_async_request',httpx.AsyncHTTPTransport.handle_async_request)
    install();fixtures();return path

@pytest.mark.parametrize('host',['graph.facebook.com','www.instagram.com','api.openai.com','private-name.never-connect.invalid'])
def test_unknown_http_denied_before_socket_and_sanitized(guard,host):
    with pytest.raises(AssertionError):httpx.post('https://'+host+'/private-path?token=private-query',headers={'Authorization':'Bearer private-auth'},json={'person':'private-body'})
    raw=guard.read_text();assert not any(v in raw for v in ('private','token','Bearer',host))
    assert json.loads(raw)['type']=='http'

def test_fixture_osm_is_not_a_network_call(guard):
    assert httpx.get('https://nominatim.openstreetmap.org/search').json()[0]['lat']=='51.66'
    assert not guard.exists()

def test_dns_and_raw_socket_escape_denied(guard):
    with pytest.raises(AssertionError):socket.getaddrinfo('person-secret.invalid',443)
    with socket.socket() as sock:
        with pytest.raises(AssertionError):sock.connect(('203.0.113.1',443))
        with pytest.raises(AssertionError):sock.connect_ex(('203.0.113.1',443))
    assert [json.loads(line)['type'] for line in guard.read_text().splitlines()]==['dns','socket','socket']
    assert 'person-secret' not in guard.read_text()

def test_negative_control_proves_failure_without_poisoning_day(guard,tmp_path):
    assert self_probe(tmp_path)['negative_control_blocked']
    assert not guard.exists()

def test_async_http_is_denied_and_recorded(guard):
    import asyncio
    async def attempt():
        async with httpx.AsyncClient() as client:
            with pytest.raises(AssertionError):await client.post('https://api.openai.com/v1/responses',json={'private':'body'})
    asyncio.run(attempt())
    assert json.loads(guard.read_text())=={'type':'http','provider':'openai'}
