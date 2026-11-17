import math
from unittest.mock import Mock
import httpx,pytest
from fastapi import HTTPException
from backend import discovery
from tests.test_api import clean,client

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv('DISCOVERY_RADIUS_ENABLED','true')
    monkeypatch.setattr(discovery,'_cache',{})
    monkeypatch.setattr(discovery,'_last_request',-float('inf'))


def response(data):return httpx.Response(200,json=data,request=httpx.Request('GET','https://test.invalid'))


def test_city_resolution_cache_and_rate_limit(monkeypatch):
    get=Mock(return_value=response([{'lat':'51.66','lon':'16.08','display_name':'Głogów, Polska'}]))
    monkeypatch.setattr(httpx,'get',get)
    result=discovery.places('Głogów')
    assert result['items'][0]['latitude']==51.66
    assert discovery.places(' GŁOGÓW ')==result
    get.assert_called_once()
    assert get.call_args.kwargs['params']['countrycodes']=='pl'
    assert get.call_args.kwargs['follow_redirects'] is False
    assert 'AiFocus3' in get.call_args.kwargs['headers']['User-Agent']
    with pytest.raises(HTTPException) as e:discovery.places('Wrocław')
    assert e.value.status_code==429


@pytest.mark.parametrize('url',['http://internal/search','https://user:secret@example.test/search','https://example.test/search?token=x'])
def test_geocoder_config_rejects_unsafe_urls(monkeypatch,url):
    monkeypatch.setenv('GEOCODING_SEARCH_URL',url)
    post=Mock(side_effect=AssertionError('HTTP forbidden'));monkeypatch.setattr(httpx,'get',post)
    with pytest.raises(HTTPException):discovery.places('Głogów')
    post.assert_not_called()


def test_radius_filters_sorts_deduplicates_and_preserves_unknowns(monkeypatch):
    near={'type':'node','id':1,'lat':51.66,'lon':16.08,'tags':{'name':'Syntetyczny salon'}}
    distant={**near,'id':2,'lat':52.66}
    way={'type':'way','id':3,'center':{'lat':51.67,'lon':16.08},'tags':{'name':'Drugi salon','addr:city':'Głogów'}}
    post=Mock(return_value=response({'elements':[distant,way,near,near,{'type':'node'},None]}));monkeypatch.setattr(httpx,'post',post)
    result=discovery.search_radius('Głogów',51.66,16.08,10)
    assert [x['name'] for x in result['items']]==['Syntetyczny salon','Drugi salon']
    item=result['items'][0]
    assert item['source_url']=='https://www.openstreetmap.org/node/1'
    assert item['distance_km']==0 and item['city']=='' and item['instagram']==''
    assert item['verification']=='requires_manual_review' and item['acquired_at']
    assert 'around:10000,51.66,16.08' in post.call_args.kwargs['data']['data']


@pytest.mark.parametrize('point',[(math.nan,16,10),(51,math.inf,10),(91,16,10),(51,16,0),(51,16,51)])
def test_bad_radius_never_calls_http(monkeypatch,point):
    post=Mock();monkeypatch.setattr(httpx,'post',post)
    with pytest.raises(HTTPException):discovery.search_radius('Głogów',*point)
    post.assert_not_called()


@pytest.mark.parametrize('data',[{}, {'elements':[], 'remark':'runtime error'}])
def test_upstream_partial_or_invalid_response_is_not_success(monkeypatch,data):
    monkeypatch.setattr(httpx,'post',lambda *a,**k:response(data))
    with pytest.raises(HTTPException) as e:discovery.search_radius('Głogów',51.66,16.08,10)
    assert e.value.status_code==503


def test_api_flag_access_validation_and_legacy_mode(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import app
    assert TestClient(app).get('/api/discovery/places?city=Głogów').status_code==401
    c=client()
    assert c.get('/api/discovery?city=Głogów&radius_km=10').status_code==422
    monkeypatch.setenv('DISCOVERY_RADIUS_ENABLED','false')
    post=Mock(return_value=response({'elements':[]}));monkeypatch.setattr(httpx,'post',post)
    assert c.get('/api/discovery/places?city=Głogów').status_code==404
    assert c.get('/api/discovery?city=Głogów&radius_km=10&latitude=51&longitude=16').status_code==404
    assert c.get('/api/discovery?city=Głogów').status_code==200
    assert c.get('/api/integrations').json()['discovery']['radius_enabled'] is False


def test_api_radius_does_not_create_salon(monkeypatch):
    c=client()
    monkeypatch.setattr(httpx,'post',lambda *a,**k:response({'elements':[]}))
    assert c.get('/api/discovery?city=Głogów&radius_km=5&latitude=51&longitude=16').status_code==200
    assert c.get('/api/salons').json()['total']==0


def test_provider_timeout_has_safe_error(monkeypatch,caplog):
    def timeout(*a,**kw):raise httpx.ReadTimeout('synthetic-private-provider-error')
    monkeypatch.setattr(httpx,'get',timeout)
    with pytest.raises(HTTPException) as e:discovery.places('Głogów')
    assert 'synthetic-private' not in str(e.value.detail)+caplog.text


def test_distance_known_symmetry():
    assert discovery.distance_km(0,0,0,1)==pytest.approx(111.195,abs=.01)
    assert discovery.distance_km(51,16,52,17)==pytest.approx(discovery.distance_km(52,17,51,16))


def test_shared_limiter_refuses_before_provider(monkeypatch):
    from types import SimpleNamespace
    db=Mock();db.bind.dialect.name='postgresql';db.scalar.return_value=False
    get=Mock();monkeypatch.setattr(httpx,'get',get)
    with pytest.raises(HTTPException) as e:discovery.places('Głogów',db)
    assert e.value.status_code==429
    get.assert_not_called()


def test_inflight_geocoder_does_not_queue_threads():
    with discovery.geocoder_slot():
        with pytest.raises(HTTPException) as e:discovery.places('Głogów')
    assert e.value.status_code==429


def test_postgres_geocoder_limit_is_shared_across_sessions(monkeypatch):
    from sqlalchemy import text
    from backend.db import Session,engine
    if engine.dialect.name!='postgresql':pytest.skip('Requires isolated PostgreSQL')
    c=client();get=Mock(return_value=response([{'lat':'51.66','lon':'16.08','display_name':'Głogów, Polska'}]));monkeypatch.setattr(httpx,'get',get)
    with Session() as other:
        other.execute(text('SELECT pg_advisory_xact_lock(603013001)'))
        assert c.get('/api/discovery/places?city=Głogów').status_code==429
        get.assert_not_called()
        other.rollback()
    assert c.get('/api/discovery/places?city=Głogów').status_code==200
    get.assert_called_once()
