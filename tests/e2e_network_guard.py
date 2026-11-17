"""Synthetic E2E deny/recorder. No actual external connection is ever attempted.
Not a production firewall: Python socket/httpx plus Playwright routing form the test guard.
"""
import fcntl,ipaddress,json,os,socket
from pathlib import Path
from sqlalchemy.engine import make_url

PROVIDERS={'graph.facebook.com':'meta','graph.instagram.com':'meta','api.instagram.com':'meta','www.instagram.com':'meta','api.openai.com':'openai','nominatim.openstreetmap.org':'osm','overpass-api.de':'osm','oauth2.googleapis.com':'google','www.googleapis.com':'google'}
def local(host):
    if host in ('localhost','127.0.0.1','::1'):return True
    try:return ipaddress.ip_address(host).is_loopback
    except (ValueError,TypeError):return False

def deny(kind,host):
    # Arbitrary hostnames can contain PII: persist only an allowlisted category.
    path=os.getenv('FOCUS_TEST_EXTERNAL_ATTEMPTS')
    if path:
        line=json.dumps({'type':kind,'provider':PROVIDERS.get(host,'other')})+'\n'
        fd=os.open(path,os.O_CREAT|os.O_APPEND|os.O_WRONLY,0o600)
        with os.fdopen(fd,'a') as out:
            fcntl.flock(out,fcntl.LOCK_EX);out.write(line);out.flush()
    raise AssertionError('External transport forbidden by synthetic E2E guard')

def install():
    target=make_url(os.getenv('DATABASE_URL','sqlite://'))
    if os.getenv('APP_ENV')!='test' or target.host not in ('localhost','127.0.0.1') or not (target.database or '').startswith('focus3_ci_'):
        raise RuntimeError('Network guard requires isolated local synthetic E2E')
    getaddrinfo=socket.getaddrinfo;connect=socket.socket.connect;connect_ex=socket.socket.connect_ex
    def checked_dns(host,*args,**kwargs):
        if not local(host):deny('dns',host)
        return getaddrinfo(host,*args,**kwargs)
    def checked_connect(sock,address):
        if sock.family in (socket.AF_INET,socket.AF_INET6) and not local(address[0]):deny('socket',address[0])
        return connect(sock,address)
    def checked_connect_ex(sock,address):
        if sock.family in (socket.AF_INET,socket.AF_INET6) and not local(address[0]):deny('socket',address[0])
        return connect_ex(sock,address)
    socket.getaddrinfo=checked_dns;socket.socket.connect=checked_connect;socket.socket.connect_ex=checked_connect_ex

def self_probe(directory):
    """An intentional blocked request uses its own ledger, not the acceptance ledger."""
    import httpx
    from unittest.mock import patch
    marker=Path(directory)/'guard-negative-control.jsonl'
    with patch.dict(os.environ,{'FOCUS_TEST_EXTERNAL_ATTEMPTS':str(marker)}):
        try:httpx.get('https://never-connect.invalid/?secret=synthetic-private-query')
        except AssertionError:pass
        else:raise AssertionError('External HTTP guard did not reject the negative control')
    events=[json.loads(line) for line in marker.read_text().splitlines()]
    if events!=[{'type':'http','provider':'other'}]:raise AssertionError('Recorder negative control failed')
    return {'negative_control_blocked':True,'record_sanitized':True}
