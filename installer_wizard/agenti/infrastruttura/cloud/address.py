import re
from urllib.parse import urlsplit, urlunsplit

from agenti.cloud.catalog import PROVIDERS

_TAILS = re.compile(r"(/chat/completions|/completions|/models|/responses|/messages)+$", re.IGNORECASE)


def _roots() -> dict[str, str]:
    roots = {}
    for spec in PROVIDERS:
        if spec.base_url:
            parts = urlsplit(spec.base_url)
            roots.setdefault((parts.hostname or "").lower(), parts.path.rstrip("/"))
    return roots


KNOWN_ROOTS = _roots()


def normalize(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
        return raw.rstrip("/")
    path = _TAILS.sub("", parts.path.rstrip("/")).rstrip("/")
    known = KNOWN_ROOTS.get((parts.hostname or "").lower())
    if known is not None:
        path = known
    elif not path:
        path = "/v1"
    return urlunsplit((parts.scheme.lower(), parts.netloc, path, "", ""))
