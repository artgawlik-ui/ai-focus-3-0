"""Local operational control, never a remote endpoint. No CRM data in status."""
import json
import logging
import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone

PAUSE_FILE=Path('/tmp/focus3-worker.pause')
STATUS_FILE=Path('/tmp/focus3-worker-status.json')


def paused():
    value=os.getenv('WORKER_PAUSED','false').strip().lower()
    return value not in ('false','0','off','no') or PAUSE_FILE.exists()


def publish(state):
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',dir=STATUS_FILE.parent,prefix='focus3-worker-',delete=False) as out:
            temporary=Path(out.name)
            json.dump({'state':state,'pid':os.getpid(),'at':datetime.now(timezone.utc).isoformat()},out)
        os.replace(temporary,STATUS_FILE)
    except OSError:
        logging.getLogger('worker').warning('Worker status write failed; details suppressed')
    finally:
        if temporary is not None:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass
