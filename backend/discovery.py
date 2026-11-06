"""Public OSM discovery. No CRM writes or communication with prospects."""
import math,os,threading,time
from datetime import datetime,timezone
from urllib.parse import urlsplit
import httpx
from contextlib import contextmanager
from sqlalchemy import text
from fastapi import HTTPException

_lock=threading.Lock()
_cache={}
_last_request=-float('inf')
USER_AGENT='AiFocus3/3.0 (https://github.com/artgawlik-ui/ai-focus-3-0)'


def enabled():return os.getenv('DISCOVERY_RADIUS_ENABLED','false').lower()=='true'


def require_enabled():
    if not enabled():raise HTTPException(404,'Wyszukiwanie promienia wyłączone')


@contextmanager
def geocoder_slot():
    if not _lock.acquire(blocking=False):raise HTTPException(429,'Geokodowanie zajęte; spróbuj później')
    try:yield
    finally:_lock.release()


def places(city,db=None):
    require_enabled()
    global _last_request
    key=' '.join(city.split()).casefold()
    if len(key)<2:raise HTTPException(422,'Podaj miejscowość')
    with geocoder_slot():
        at=time.monotonic()
        if key in _cache and at-_cache[key][0]<86400:return _cache[key][1]
        if at-_last_request<1:raise HTTPException(429,'Odczekaj sekundę przed kolejnym wyszukiwaniem',headers={'Retry-After':'1'})
        url=os.getenv('GEOCODING_SEARCH_URL','https://nominatim.openstreetmap.org/search')
        parsed=urlsplit(url)
        if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise HTTPException(503,'Nieprawidłowa konfiguracja geokodowania')
        shared=db is not None and db.bind.dialect.name=='postgresql'
        if shared and not db.scalar(text('SELECT pg_try_advisory_xact_lock(603013001)')):
            raise HTTPException(429,'Geokodowanie zajęte; spróbuj później',headers={'Retry-After':'1'})
        _last_request=at
        try:
            try:
                r=httpx.get(url,params={'city':city,'countrycodes':'pl','format':'jsonv2','limit':5},headers={'User-Agent':USER_AGENT},timeout=10,follow_redirects=False)
            finally:
                # Held in request's transaction through close; across overlapping API processes.
                if shared:time.sleep(max(0,1-(time.monotonic()-at)))
            r.raise_for_status();data=r.json()
            if not isinstance(data,list):raise ValueError()
            items=[]
            for row in data[:5]:
                try:
                    lat=float(row['lat']);lon=float(row['lon']);label=row['display_name']
                    if not valid_point(lat,lon) or not isinstance(label,str):continue
                    items.append({'label':label[:400],'latitude':lat,'longitude':lon})
                except (KeyError,ValueError,TypeError):continue
        except Exception:raise HTTPException(503,'Geokodowanie chwilowo niedostępne') from None
        if len(_cache)>=128:_cache.pop(next(iter(_cache)))
        result={'items':items,'source':'© OpenStreetMap contributors, ODbL'}
        _cache[key]=(at,result)
        return result


def valid_point(lat,lon):return math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180


def distance_km(a,b,c,d):
    x,y=math.radians(c-a),math.radians(d-b)
    v=math.sin(x/2)**2+math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(y/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1,max(0,v))))


def search_radius(city,latitude,longitude,radius_km):
    require_enabled()
    if not valid_point(latitude,longitude) or not math.isfinite(radius_km) or not 1<=radius_km<=50:
        raise HTTPException(422,'Nieprawidłowy punkt lub promień')
    query=f'[out:json][timeout:20];nwr["shop"="hairdresser"](around:{int(radius_km*1000)},{latitude},{longitude});out center tags 100;'
    try:
        r=httpx.post('https://overpass-api.de/api/interpreter',data={'data':query},headers={'User-Agent':USER_AGENT},timeout=30,follow_redirects=False)
        r.raise_for_status();data=r.json()
        if not isinstance(data,dict) or not isinstance(data.get('elements'),list) or data.get('remark'):raise ValueError()
    except Exception:raise HTTPException(503,'Wyszukiwanie OSM chwilowo niedostępne') from None
    acquired=datetime.now(timezone.utc).isoformat();items=[];seen=set()
    for row in data['elements'][:100]:
        try:
            kind=row['type'];identity=row['id'];tags=row['tags'];center=row.get('center',row)
            if kind not in ('node','way','relation') or type(identity)!=int or identity<=0 or not isinstance(tags,dict):continue
            lat=float(center['lat']);lon=float(center['lon'])
            if not valid_point(lat,lon):continue
            distance=distance_km(latitude,longitude,lat,lon)
            if distance>radius_km or (kind,identity) in seen:continue
            seen.add((kind,identity))
            def field(name):
                v=tags.get(name,'')
                return v[:300] if isinstance(v,str) else ''
            items.append({'name':field('name') or 'Salon bez nazwy','city':field('addr:city'),'address':' '.join(filter(None,[field('addr:street'),field('addr:housenumber')])),'phone':field('phone'),'instagram':'','specialization':'','source_url':f'https://www.openstreetmap.org/{kind}/{identity}','acquired_at':acquired,'verification':'requires_manual_review','distance_km':round(distance,2),'latitude':lat,'longitude':lon})
        except (KeyError,TypeError,ValueError):continue
    items.sort(key=lambda item:(item['distance_km'],item['source_url']))
    return {'items':items,'source':'© OpenStreetMap contributors, ODbL','center':{'latitude':latitude,'longitude':longitude,'label':city},'radius_km':radius_km,'acquired_at':acquired,'limit':100,'note':'Dane publiczne wymagają weryfikacji. Wyniki mogą być niekompletne; odległość w linii prostej.'}
