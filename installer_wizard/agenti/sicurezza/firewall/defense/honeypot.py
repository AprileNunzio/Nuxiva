import asyncio
import logging
import time
from collections import deque

from agenti.firewall.defense import netaddr

PORT = 47_022
BANNER = b"SSH-2.0-OpenSSH_9.6\r\n"
HOLD = 45.0
READ = 512
MAX_CLIENTS = 64
log = logging.getLogger("nuxiva.firewall")


class Honeypot:

    def __init__(self) -> None:
        self.server: asyncio.base_events.Server | None = None
        self.clients = 0
        self.touches: deque[dict] = deque(maxlen=200)
        self.allowed: set[str] = set()

    def allow(self, addresses) -> None:
        self.allowed = {netaddr.canonical(a) for a in addresses}

    async def _session(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername") or ("", 0)
        source = netaddr.canonical(str(peer[0]))
        if source not in self.allowed or self.clients >= MAX_CLIENTS:
            writer.close()
            return
        self.clients += 1
        started, received = time.time(), 0
        try:
            writer.write(BANNER)
            await writer.drain()
            while time.time() - started < HOLD:
                try:
                    chunk = await asyncio.wait_for(reader.read(READ), timeout=HOLD)
                except asyncio.TimeoutError:
                    break
                if not chunk:
                    break
                received += len(chunk)
                await asyncio.sleep(5)
        except (ConnectionError, OSError):
            pass
        finally:
            self.clients -= 1
            self.touches.append({"src": source, "at": started, "seconds": round(time.time() - started, 1), "bytes": received})
            writer.close()

    async def start(self) -> bool:
        if self.server is not None:
            return True
        try:
            self.server = await asyncio.start_server(self._session, host=None, port=PORT, reuse_address=True, limit=READ)
        except OSError as exc:
            log.warning("Esca isolata non avviata sulla porta %d: %s", PORT, exc)
            return False
        return True

    async def stop(self) -> None:
        server, self.server = self.server, None
        if server is not None:
            server.close()
            await server.wait_closed()

    def status(self) -> dict:
        return {"running": self.server is not None, "port": PORT, "clients": self.clients, "touches": list(self.touches)[-20:]}


honeypot = Honeypot()
