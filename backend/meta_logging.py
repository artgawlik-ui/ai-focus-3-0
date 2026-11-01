"""Provider wire logs can contain required query secrets: suppress them entirely.

Do not attach raw httpx requests/exceptions to monitoring. API handlers and workers
use fixed error categories, never exception repr/str or exc_info.
"""
import logging

class NoProviderWireLogs(logging.Filter):
    def filter(self,record):return False

def install():
    for name in ('httpx','httpcore','httpcore.connection','httpcore.http11','httpcore.http2','httpcore.proxy','httpcore.socks'):
        logger=logging.getLogger(name)
        logger.setLevel(logging.CRITICAL+1)
        logger.addFilter(NoProviderWireLogs())
