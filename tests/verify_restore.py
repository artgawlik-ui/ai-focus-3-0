"""End-to-end backup test, using only isolated local test databases."""
import os, secrets
from pathlib import Path
from scripts.backup import backup, restore, fingerprint
os.environ['DATABASE_URL']='postgresql://postgres@127.0.0.1:55432/focus3_e2e'
os.environ['RESTORE_DATABASE_URL']='postgresql://postgres@127.0.0.1:55432/focus3_restore'
os.environ['BACKUP_PASSPHRASE']=secrets.token_urlsafe(40)
os.environ['PATH']=str(Path('.tools').resolve())+os.pathsep+os.environ['PATH']
path=Path('/tmp/focus3-restore-test.enc')
if path.exists():path.unlink()
backup(str(path));restore(str(path))
assert fingerprint(os.environ['DATABASE_URL'])==fingerprint(os.environ['RESTORE_DATABASE_URL'])
print('Encrypted backup round-trip: PASS, table counts and SHA-256 fingerprints match')
try:restore(str(path))
except ValueError:print('Restore into nonempty target: correctly refused')
else:raise AssertionError('Unsafe restore accepted')
path.unlink()
