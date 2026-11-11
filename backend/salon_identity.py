"""Conservative normalization of manually verified Instagram profile references.

This function does NOT verify account ownership, permission to contact, or Meta
recipient IDs. It is intended for candidate matching in CRM only.
"""
import re
from urllib.parse import urlsplit

_USERNAME = re.compile(r"^[a-z0-9._]{1,30}$", re.ASCII)
_NON_PROFILE_PATHS = frozenset({
    "p", "reel", "reels", "stories", "explore", "direct", "accounts",
    "about", "developer", "developers", "privacy", "legal", "api",
})


def instagram_username(value: str | None) -> str | None:
    """Return a conservative lowercase username or None for unknown input.

    Supports @handle, handle, and https://(www.)instagram.com/handle/.
    Never assumes that posts, reels, links on other hosts, or arbitrary
    free-text are an account identifier.
    """
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.startswith("@"):
        candidate = raw[1:]
    elif "://" in raw:
        try:
            url = urlsplit(raw)
            if url.scheme.lower() != "https":
                return None
            if url.username or url.password or url.port:
                return None
            if (url.hostname or "").lower() not in {
                "instagram.com", "www.instagram.com",
            }:
                return None
            parts = [part for part in url.path.split("/") if part]
            if len(parts) != 1:
                return None
            candidate = parts[0]
        except ValueError:
            return None
    else:
        candidate = raw
    candidate = candidate.lower()
    if not _USERNAME.fullmatch(candidate):
        return None
    if candidate in _NON_PROFILE_PATHS:
        return None
    return candidate
