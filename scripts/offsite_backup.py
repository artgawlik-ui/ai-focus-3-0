"""Opt-in daily encrypted S3 backup in existing service; no resource provisioning.
Bucket lifecycle (30 days) must be configured and confirmed before enabling.
"""
import hashlib,hmac,os,tempfile,time,logging
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote,urlsplit
import httpx
from scripts.backup import backup
log=logging.getLogger('backup')

def signed_put(url,body,key,secret,region,at=None):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('HTTPS object URL without credentials or query required')
    at=at or datetime.now(timezone.utc);stamp=at.strftime('%Y%m%dT%H%M%SZ');day=stamp[:8]
    content_hash=hashlib.sha256(body).hexdigest()
    headers={'host':parsed.netloc,'x-amz-content-sha256':content_hash,'x-amz-date':stamp}
    canonical_headers=''.join(k+':'+v+'\n' for k,v in sorted(headers.items()))
    names=';'.join(sorted(headers))
    canonical='\n'.join(['PUT',parsed.path or '/','',canonical_headers,names,content_hash])
    scope=day+'/'+region+'/s3/aws4_request'
    to_sign='AWS4-HMAC-SHA256\n'+stamp+'\n'+scope+'\n'+hashlib.sha256(canonical.encode()).hexdigest()
    def sign(k,v):return hmac.new(k,v.encode(),hashlib.sha256).digest()
    signing=sign(sign(sign(sign(('AWS4'+secret).encode(),day),region),'s3'),'aws4_request')
    signature=hmac.new(signing,to_sign.encode(),hashlib.sha256).hexdigest()
    headers['Authorization']='AWS4-HMAC-SHA256 Credential='+key+'/'+scope+', SignedHeaders='+names+', Signature='+signature
    return headers

def run_once():
    if os.getenv('OFFSITE_BACKUP_ENABLED','false').lower()!='true':return False
    if os.getenv('BACKUP_RETENTION_CONFIRMED_DAYS')!='30':raise ValueError('Configure and confirm 30-day bucket lifecycle first')
    root=os.environ['BACKUP_S3_PREFIX_URL'].rstrip('/')
    filename='focus3-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.enc'
    url=root+'/'+quote(filename)
    with tempfile.TemporaryDirectory(prefix='focus3-backup-') as directory:
        path=Path(directory)/filename;backup(str(path));body=path.read_bytes()
        headers=signed_put(url,body,os.environ['BACKUP_S3_ACCESS_KEY_ID'],os.environ['BACKUP_S3_SECRET_ACCESS_KEY'],os.environ['BACKUP_S3_REGION'])
        # No redirects: never send authorization to another endpoint.
        response=httpx.put(url,content=body,headers=headers,timeout=180,follow_redirects=False)
        if response.status_code not in (200,201,204):raise RuntimeError('Offsite upload failed')
    log.info('backup uploaded encrypted=true retention_days=30')
    return True

def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:run_once();delay=86400
        except Exception:log.error('backup failed; check configuration/storage; secret values suppressed');delay=3600
        time.sleep(delay)

if __name__=='__main__':main()
