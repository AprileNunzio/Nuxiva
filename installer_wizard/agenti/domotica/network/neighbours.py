import ipaddress
import logging
from pathlib import Path

log = logging.getLogger("nuxiva.network.neighbours")
ARP_TABLE = Path("/proc/net/arp")
COMPLETE = "0x2"


def parse(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4 or parts[2] != COMPLETE:
            continue
        try:
            ip = str(ipaddress.IPv4Address(parts[0]))
        except ValueError:
            continue
        out[ip] = parts[3].lower()
    return out


def table(path: Path = ARP_TABLE) -> dict[str, str]:
    try:
        return parse(path.read_text(encoding="ascii", errors="replace"))
    except OSError as exc:
        log.info("Tabella ARP non leggibile: %s", type(exc).__name__)
        return {}
