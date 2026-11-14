import asyncio
import logging
import os
import socket

from agenti.collaudo import hub, paths

log = logging.getLogger("nuxiva.collaudo")


class Intake(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.rejected = 0

    def datagram_received(self, data: bytes, addr) -> None:
        try:
            hub.get().emit(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, RuntimeError, OSError):
            self.rejected += 1


async def serve() -> asyncio.DatagramTransport:
    loop = asyncio.get_running_loop()
    paths.ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    if paths.SOCKET.exists():
        paths.SOCKET.unlink()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(str(paths.SOCKET))
    os.chmod(paths.SOCKET, 0o600)
    sock.setblocking(False)
    transport, _ = await loop.create_datagram_endpoint(Intake, sock=sock)
    return transport
