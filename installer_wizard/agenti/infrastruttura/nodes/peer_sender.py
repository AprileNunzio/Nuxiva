import asyncio
import ipaddress
import json
import logging
import socket

from config import PUBLIC_PORT

from agenti.nodes import peer_envelope
from agenti.nodes.peer_identity import identity
from agenti.nodes.peer_ledger import ledger

log = logging.getLogger("nuxiva.peer")

PEER_PORT = 50507
EVERY = 10
MAX_DATAGRAM = 1200


def https_port() -> int:
    try:
        from agenti.secure import api as secure
        return int(secure._active.get("port") or 0)
    except (ImportError, AttributeError, TypeError, ValueError):
        return 0


def local_addresses() -> list[str]:
    found: list[str] = []
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        infos = []
    for info in infos:
        found.append(info[4][0])
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        found.append(probe.getsockname()[0])
    except OSError:
        pass
    finally:
        probe.close()
    unique: list[str] = []
    for raw in found:
        ip = ipaddress.ip_address(raw)
        if ip.is_loopback or ip.is_unspecified or ip.is_link_local or ip.is_multicast or raw in unique:
            continue
        unique.append(raw)
    return unique[: peer_envelope.MAX_ADDRS]


def build_record(port: int | None = None, addresses=local_addresses) -> bytes | None:
    port = port or https_port() or PUBLIC_PORT
    addrs = [f"{ip}:{port}" for ip in addresses()]
    if not addrs:
        return None
    ledger.announce(addrs)
    data = json.dumps(identity().seal_locate(addrs), separators=(",", ":")).encode("utf-8")
    return data if len(data) <= MAX_DATAGRAM else None


class PeerSender:
    def __init__(self, target: tuple[str, int] = ("255.255.255.255", PEER_PORT), every: float = EVERY) -> None:
        self.target, self.every = target, every

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            transport, _ = await loop.create_datagram_endpoint(asyncio.DatagramProtocol, family=socket.AF_INET, allow_broadcast=True)
        except OSError as exc:
            log.warning("Invio periodico degli indirizzi non disponibile: %s", exc)
            return
        try:
            while True:
                try:
                    record = await asyncio.to_thread(build_record)
                    if record:
                        transport.sendto(record, self.target)
                except (OSError, ValueError) as exc:
                    log.debug("Indirizzi non inviati: %s", exc)
                await asyncio.sleep(self.every)
        finally:
            transport.close()


sender = PeerSender()
