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


def test_failed_fixture_bootstrap_exits_before_application(tmp_path):
    import os,subprocess,sys
    from pathlib import Path
    # Python normally ignores sitecustomize errors: this bootstrap must fail closed.
    source=(Path(__file__).parent/'ci_e2e.py').read_text()
    import ast
    tree=ast.parse(source)
    assignment=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write_text' and n.args and isinstance(n.args[0],ast.Constant) and 'os._exit(78)' in str(n.args[0].value))
    (tmp_path/'sitecustomize.py').write_text(assignment.args[0].value)
    env={'PATH':os.environ.get('PATH',''),'APP_ENV':'production','DATABASE_URL':'postgresql://postgres@127.0.0.1/focus3_ci_synthetic','PYTHONPATH':str(tmp_path)+os.pathsep+str(Path(__file__).resolve().parents[1])}
    result=subprocess.run([sys.executable,'-c','raise SystemExit(0)'],env=env,capture_output=True,timeout=10)
    assert result.returncode==78


def test_google_fixture_is_local_and_etag_protected(monkeypatch,tmp_path):
    monkeypatch.setenv('APP_ENV','test');monkeypatch.setenv('DATABASE_URL','postgresql://postgres@127.0.0.1/focus3_ci_synthetic')
    monkeypatch.setenv('FOCUS_TEST_GOOGLE_STORE',str(tmp_path/'google.json'))
    monkeypatch.setattr(httpx.HTTPTransport,'handle_request',httpx.HTTPTransport.handle_request)
    monkeypatch.setattr(httpx.AsyncHTTPTransport,'handle_async_request',httpx.AsyncHTTPTransport.handle_async_request)
    install()
    root='https://www.googleapis.com/calendar/v3'
    calendar=httpx.post(root+'/calendars',json={'summary':'Syntetyczny kalendarz'}).json()['id']
    path=root+'/calendars/'+calendar+'/events'
    first=httpx.post(path,params={'sendUpdates':'none'},json={'id':'fixture-event','status':'confirmed'})
    assert first.status_code==200
    assert httpx.post(path,params={'sendUpdates':'none'},json={'id':'fixture-event'}).status_code==409
    assert httpx.patch(path+'/fixture-event',params={'sendUpdates':'none'},headers={'If-Match':'wrong'},json={'status':'cancelled'}).status_code==412
    assert httpx.patch(path+'/fixture-event',params={'sendUpdates':'none'},headers={'If-Match':first.json()['etag']},json={'status':'cancelled'}).json()['status']=='cancelled'
