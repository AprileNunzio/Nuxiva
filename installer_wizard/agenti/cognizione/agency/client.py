import asyncio
import json
import os
from pathlib import Path

SOCKET = Path(os.environ.get("NUXIVA_AGENCY_SOCKET", "/run/nuxiva/agency/agency.sock"))
LIMIT = 1024 * 1024
TIMEOUT = 15.0


class AgencyUnavailable(RuntimeError):
    pass


class AgencyRejected(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AgencyClient:
    def __init__(self, socket_path: Path = SOCKET, timeout: float = TIMEOUT) -> None:
        self.socket_path = socket_path
        self.timeout = timeout

    async def call(self, op: str, **fields):
        payload = json.dumps({"op": op, **fields}, ensure_ascii=False).encode() + b"\n"
        if len(payload) > LIMIT:
            raise AgencyRejected("too_large", "request too large")
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(str(self.socket_path), limit=LIMIT), self.timeout)
        except (OSError, asyncio.TimeoutError) as exc:
            raise AgencyUnavailable(type(exc).__name__) from exc
        try:
            writer.write(payload)
            await asyncio.wait_for(writer.drain(), self.timeout)
            line = await asyncio.wait_for(reader.readline(), self.timeout)
        except (OSError, asyncio.TimeoutError, ValueError) as exc:
            raise AgencyUnavailable(type(exc).__name__) from exc
        finally:
            writer.close()
        try:
            reply = json.loads(line)
        except ValueError as exc:
            raise AgencyUnavailable("malformed reply") from exc
        if not isinstance(reply, dict):
            raise AgencyUnavailable("malformed reply")
        if not reply.get("ok"):
            error = reply.get("error") if isinstance(reply.get("error"), dict) else {}
            raise AgencyRejected(str(error.get("code", "error")), str(error.get("message", "")))
        return reply.get("data")


client = AgencyClient()
