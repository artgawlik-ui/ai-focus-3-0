"""Publiczna walidacja produkcji: wyłącznie GET, bez logowania i tokenów Meta."""
import argparse,json,time
from pathlib import Path
import httpx

def check(expected_version):
    origin='https://ai-focus-3-0.onrender.com'
    result={'origin':origin,'expected_version':expected_version,'requests':{},'mutations':0}
    with httpx.Client(base_url=origin,follow_redirects=False,timeout=20) as client:
        for path,expected in (('/api/health',200),('/api/auth/me',401),('/api/salons',401),('/api/meta/status',401),('/api/meta/webhook',404),('/api/meta/oauth/callback',404),('/manifest.webmanifest',200),('/sw.js',200)):
            start=time.monotonic();response=client.get(path)
            item={'status':response.status_code,'expected_status':expected,'duration_ms':round(1000*(time.monotonic()-start))}
            result['requests'][path]=item
            assert response.status_code==expected,'Nieoczekiwany status publicznego endpointu'
            if path.startswith('/api/'):
                item['no_store']=response.headers.get('cache-control')=='no-store'
                item['hsts']='max-age=' in response.headers.get('strict-transport-security','')
                item['nosniff']=response.headers.get('x-content-type-options')=='nosniff'
                item['frame_deny']=response.headers.get('x-frame-options')=='DENY'
                item['csp']="frame-ancestors 'none'" in response.headers.get('content-security-policy','')
                assert all(item[k] for k in ('no_store','hsts','nosniff','frame_deny','csp')),'Brak nagłówka bezpieczeństwa'
            if path=='/api/health':
                data=response.json();item['version']=data.get('version');assert data.get('status')=='ok' and data.get('version')==expected_version,'Nieoczekiwana wersja produkcji'
            if path=='/manifest.webmanifest':
                item['standalone']=response.json().get('display')=='standalone';assert item['standalone'],'Nieprawidłowy manifest'
    result['status']='PASS'
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--expected-version',required=True);parser.add_argument('--output',default='test-results/meta-production-readonly.json');args=parser.parse_args()
    try:result=check(args.expected_version)
    except Exception:raise SystemExit('Walidacja odczytowa nie powiodła się; nie ujawniono odpowiedzi ani sekretów')
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print('Odczytowa walidacja HTTPS, bramek Meta i nagłówków: PASS')
