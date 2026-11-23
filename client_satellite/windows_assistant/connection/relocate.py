import http.client
import logging
import ssl
import threading

from connection import tls
from connection.client import endpoint

log = logging.getLogger("nuxiva.peer")

MAX_TRIES = 3
PROBE_TIMEOUT = 4.0


def server_url(addr: str) -> str:
    host, _, port = addr.rpartition(":")
    return f"https://{host}" if port == "443" else f"https://{host}:{port}"


def reachable(url: str, ca_pem: str, timeout: float = PROBE_TIMEOUT) -> bool:
    host, port = endpoint(url)
    conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=tls.pinned_context(ca_pem))
    try:
        conn.connect()
    except (OSError, ssl.SSLError, http.client.HTTPException):
        return False
    finally:
        conn.close()
    return True


class Relocator:
    def __init__(self, client, cfg: dict, is_online, save, probe=reachable) -> None:
        self.client, self.cfg, self.is_online, self.save, self.probe = client, cfg, is_online, save, probe
        self.lock = threading.Lock()

    def offer(self, addrs: list[str]) -> bool:
        if self.is_online() or not self.lock.acquire(blocking=False):
            return False
        try:
            current = endpoint(self.client.server)
            for addr in addrs[:MAX_TRIES]:
                url = server_url(addr)
                if endpoint(url) == current or not self.probe(url, self.client.ca_pem):
                    continue
                if self.is_online():
                    return False
                log.info("Il server è stato ritrovato a un nuovo indirizzo: %s", url)
                self.client.server = self.cfg["server"] = url
                self.save(self.cfg)
                return True
            return False
        finally:
            self.lock.release()
