"""Loaded only by isolated CI site's sitecustomize. Never a production import."""
import httpx,os,json,fcntl
from pathlib import Path
from sqlalchemy.engine import make_url


def install():
    target=make_url(os.environ.get('DATABASE_URL','sqlite://'))
    if os.getenv('APP_ENV')!='test' or target.host not in ('localhost','127.0.0.1') or not (target.database or '').startswith('focus3_ci_'):
        raise RuntimeError('Synthetic transport requires isolated local E2E database')
    original=httpx.HTTPTransport.handle_request
    async_original=httpx.AsyncHTTPTransport.handle_async_request
    def google_fixture(request):
        path=os.getenv('FOCUS_TEST_GOOGLE_STORE')
        if not path:raise AssertionError('Google fixture storage required')
        with open(path,'a+') as out:
            fcntl.flock(out,fcntl.LOCK_EX);out.seek(0);raw=out.read();store=json.loads(raw) if raw else {'calendars':0,'events':{},'counter':0}
            route=request.url.path;body=json.loads(request.read() or b'{}')
            if route.endswith('/calendars'):
                store['calendars']+=1;result={'id':'fixture-calendar-'+str(store['calendars'])};code=200
            elif request.method=='GET':
                result=store['events'].get(route,{});code=200 if result else 404
            elif request.method=='POST':
                assert request.url.params.get('sendUpdates')=='none'
                key=route+'/'+body['id']
                if key in store['events']:result={};code=409
                else:
                    store['counter']+=1;result={**body,'etag':'fixture-etag-'+str(store['counter'])};store['events'][key]=result;code=200
            elif request.method=='PATCH':
                assert request.url.params.get('sendUpdates')=='none'
                current=store['events'].get(route,{})
                if request.headers.get('If-Match')!=current.get('etag'):result={};code=412
                else:
                    store['counter']+=1;result={**current,**body,'etag':'fixture-etag-'+str(store['counter'])};store['events'][route]=result;code=200
            else:raise AssertionError('Unexpected Google fixture operation')
            out.seek(0);out.truncate();json.dump(store,out);out.flush()
        return httpx.Response(code,json=result,request=request)
    def fixture(request):
        if request.url.host=='oauth2.googleapis.com':
            assert request.method=='POST' and request.url.path=='/token'
            return httpx.Response(200,json={'access_token':'synthetic-google-access','refresh_token':'synthetic-google-refresh','expires_in':3600,'scope':'https://www.googleapis.com/auth/calendar.app.created'},request=request)
        if request.url.host=='www.googleapis.com':return google_fixture(request)
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
