"""Domyślna izolacja narzędzi operatorskich; bez odczytu sekretów i sieci."""
import os
from urllib.parse import urlsplit


def local_origin(value=None):
    origin = value if value is not None else os.getenv('FOCUS_TEST_ORIGIN', 'http://127.0.0.1:8005')
    try:
        parsed = urlsplit(origin)
        valid = (parsed.scheme in ('http', 'https') and parsed.hostname in ('localhost', '127.0.0.1', '::1')
                 and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
                 and parsed.path in ('', '/') and parsed.port is not None)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Narzędzie testowe wymaga jawnego lokalnego adresu z portem')
    return origin.rstrip('/')


def require_historical_artifact_consent():
    """Starsze narzędzia nie mogą samoczynnie czytać historycznych danych."""
    if os.getenv('FOCUS_ALLOW_HISTORICAL_PRIVATE_ARTIFACTS') != 'explicitly-authorized':
        raise SystemExit('Historyczne prywatne artefakty zablokowane; użyj danych syntetycznych')
