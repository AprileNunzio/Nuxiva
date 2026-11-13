import asyncio
import json
import logging
import time

import websockets

from agenti.firewall.defense import view

URL = "ws://127.0.0.1:8093/rescue"
WATCH_S = 600.0
CONNECT_S = 5.0
MAX_TARGETS = 6
log = logging.getLogger("nuxiva.firewall")


def scene() -> dict:
    from agenti.firewall.defense.guardian import guardian
    data = view.build()
    rows = guardian.assessment.get("incidents", [])[:view.MAX_INCIDENTS]
    targets = {row["id"]: [str(t)[:64] for t in row["targets"][:MAX_TARGETS]] for row in rows}
    return {**data, "incidents": [{**i, "hosts": targets.get(i["id"], [])} for i in data["incidents"]]}


class Stage:

    def __init__(self) -> None:
        self.ws = None
        self.reader: asyncio.Task | None = None
        self.watch_until = 0.0
        self.sent = "calm"
        self.lock = asyncio.Lock()

    async def _drain(self, ws) -> None:
        try:
            async for _ in ws:
                pass
        except (websockets.WebSocketException, OSError):
            return

    async def _socket(self):
        if self.ws is not None and self.ws.close_code is None:
            return self.ws
        self.ws = await asyncio.wait_for(websockets.connect(URL, max_size=2 ** 16, open_timeout=CONNECT_S), CONNECT_S + 1)
        self.reader = asyncio.get_running_loop().create_task(self._drain(self.ws))
        return self.ws

    async def send(self, message: dict) -> bool:
        async with self.lock:
            try:
                ws = await self._socket()
                await ws.send(json.dumps(message, separators=(",", ":")))
                return True
            except (websockets.WebSocketException, OSError, asyncio.TimeoutError) as exc:
                log.debug("Vista della difesa non consegnata allo schermo: %s", exc)
                self.ws = None
                return False

    async def show(self, opened: bool = True) -> bool:
        if opened:
            self.watch_until = time.time() + WATCH_S
        return await self.send({"type": "defense_view", "open": opened, "scene": scene()})

    async def close(self) -> bool:
        self.watch_until = 0.0
        return await self.send({"type": "defense_view", "open": False})

    async def update(self, posture: str) -> None:
        if time.time() >= self.watch_until:
            return
        self.sent = posture
        await self.send({"type": "defense_state", "scene": scene()})


stage = Stage()
