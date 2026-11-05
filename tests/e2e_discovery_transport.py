"""Loaded only by isolated CI site's sitecustomize. Never a production import."""
import httpx,os
from sqlalchemy.engine import make_url


def install():
    target=make_url(os.environ.get('DATABASE_URL','sqlite://'))
    if os.getenv('APP_ENV')!='test' or target.host not in ('localhost','127.0.0.1') or not (target.database or '').startswith('focus3_ci_'):
        raise RuntimeError('Synthetic transport requires isolated local E2E database')
    original=httpx.HTTPTransport.handle_request
    async_original=httpx.AsyncHTTPTransport.handle_async_request
    def fixture(request):
        if request.url.host=='nominatim.openstreetmap.org':
            return httpx.Response(200,json=[{'lat':'51.66','lon':'16.08','display_name':'Głogów, syntetyczne centrum'}],request=request)
        if request.url.host=='overpass-api.de':
            return httpx.Response(200,json={'elements':[{'type':'node','id':900000000001,'lat':51.67,'lon':16.08,'tags':{'name':'[TEST] Salon promień','addr:city':'Głogów','addr:street':'Syntetyczna','addr:housenumber':'1'}}]},request=request)
        if request.url.host not in ('localhost','127.0.0.1','::1'):
            raise AssertionError('External HTTP forbidden in synthetic E2E')
        return None
    def handle(self,request):
        result=fixture(request)
        return result if result is not None else original(self,request)
    async def async_handle(self,request):
        result=fixture(request)
        return result if result is not None else await async_original(self,request)
    httpx.HTTPTransport.handle_request=handle
    httpx.AsyncHTTPTransport.handle_async_request=async_handle
