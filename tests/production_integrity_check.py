"""Read-only table fingerprint comparison across a production service redeploy."""
import os,json,sys
from pathlib import Path
import httpx
origin='https://ai-focus-3-0.onrender.com'
private=Path('.render-auth')
credentials=json.loads((private/'verification.json').read_text())
client=httpx.Client(base_url=origin,timeout=40)
sessionfile=private/'audit-session.json'
if sessionfile.exists():
    saved=json.loads(sessionfile.read_text());client.cookies.update(saved['cookies']);client.headers['X-CSRF-Token']=saved['csrf']
else:
    r=client.post('/api/auth/login',json={k:credentials[k] for k in ['email','password']});r.raise_for_status()
    saved={'cookies':dict(client.cookies),'csrf':r.json()['csrf']}
    sessionfile.write_text(json.dumps(saved));sessionfile.chmod(0o600)
    client.headers['X-CSRF-Token']=saved['csrf']
result=client.get('/api/admin/integrity');result.raise_for_status();snapshot=result.json()
if sys.argv[1]=='baseline':
    (private/'integrity-baseline.json').write_text(json.dumps(snapshot))
    print('Read-only production baseline captured: '+str(len(snapshot['tables']))+' tables')
else:
    before=json.loads((private/'integrity-baseline.json').read_text())
    differences=[name for name,data in before['tables'].items() if snapshot['tables'].get(name)!=data]
    assert not differences,'Changed tables across redeploy: '+','.join(differences)
    report={'status':'PASS','all_counts_match':True,'all_sha256_match':True,'tables':snapshot['tables']}
    Path('test-results/production-redeploy-integrity.json').write_text(json.dumps(report,indent=2))
    print('PASS: record counts and SHA-256 fingerprints of all '+str(len(snapshot['tables']))+' tables unchanged after redeploy')
