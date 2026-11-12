import re

SHARE_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}")
MODES = frozenset({"read", "write"})


def valid_share_grants(value) -> bool:
    return isinstance(value, dict) and len(value) <= 128 and all(
        isinstance(share, str) and SHARE_ID.fullmatch(share)
        and isinstance(mode, str) and mode in MODES
        for share, mode in value.items()
    )
