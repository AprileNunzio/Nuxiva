import asyncio
import logging
from collections import deque

import websockets


log = logging.getLogger("nuxiva.ear.delivery")
MAX_PENDING = 64
SEND_TIMEOUT = 2.0


class EventDelivery:
    def __init__(self, session):
        self.session = session
        self.pending = deque()
        self.ready = asyncio.Event()
        self.closed = False
        self.failed = False
        self.closer = None
        self.task = asyncio.create_task(self.run())

    def put(self, event, data):
        if self.closed:
            return
        if event == "level":
            self.pending = deque((kind, payload) for kind, payload in self.pending if kind != "level")
        if len(self.pending) >= MAX_PENDING:
            self.failed = True
            log.warning("Slow ear client exceeded delivery queue; closing this connection")
            self.closer = asyncio.create_task(self.disconnect())
            self.close()
            return
        self.pending.append((event, data))
        self.ready.set()

    def close(self):
        self.closed = True
        self.pending.clear()
        self.task.cancel()

    async def run(self):
        try:
            while not self.closed:
                await self.ready.wait()
                while self.pending:
                    _, data = self.pending.popleft()
                    await asyncio.wait_for(self.session.ws.send(data), SEND_TIMEOUT)
                self.ready.clear()
        except asyncio.CancelledError:
            raise
        except (websockets.ConnectionClosed, RuntimeError, OSError, asyncio.TimeoutError) as exc:
            self.failed = True
            log.warning("Ear client delivery failed: %s", exc)
        except Exception:
            self.failed = True
            log.exception("Unexpected ear client delivery failure")
        finally:
            self.closed = True
            self.pending.clear()
            if self.failed:
                if self.closer is None:
                    self.closer = asyncio.create_task(self.disconnect())
                await self.closer

    async def disconnect(self):
        try:
            await asyncio.wait_for(self.session.ws.close(code=1013, reason="ear_delivery_backpressure"), 1.0)
        except (websockets.ConnectionClosed, RuntimeError, OSError, asyncio.TimeoutError) as exc:
            log.debug("Ear connection cleanup: %s", exc)


def enqueue(session, event, data):
    delivery = getattr(session, "_ear_delivery", None)
    if not isinstance(delivery, EventDelivery):
        delivery = EventDelivery(session)
        session._ear_delivery = delivery
    delivery.put(event, data)


def close_delivery(session):
    delivery = getattr(session, "_ear_delivery", None)
    if isinstance(delivery, EventDelivery):
        delivery.close()
