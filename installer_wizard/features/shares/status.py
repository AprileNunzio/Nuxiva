import logging
import re

from config import DEMO

log = logging.getLogger("nuxiva.shares")

LINE = re.compile(r"^\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+\(([^)]+)\)\s+(\S+)\s+(\S+)\s+(\S+)\s*$")


def parse(output: str) -> list[dict]:
    sessions = []
    for line in output.splitlines():
        match = LINE.match(line)
        if match:
            pid, user, _, machine, address, protocol, encryption, signing = match.groups()
            sessions.append({"pid": int(pid), "user": user, "machine": machine[:60], "address": address[:60],
                             "protocol": protocol, "encryption": encryption, "signing": signing})
    return sessions[:50]


async def sessions() -> list[dict]:
    if DEMO:
        return []
    from health import sh
    try:
        code, out = await sh("smbstatus", "-b", timeout=6)
    except Exception as exc:
        log.info("smbstatus non disponibile: %s", exc)
        return []
    return parse(out) if code == 0 else []
