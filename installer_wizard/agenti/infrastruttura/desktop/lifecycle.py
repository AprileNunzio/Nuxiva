import asyncio
import json
import logging
import os
import re
from pathlib import Path

SOCKET = Path(os.environ.get("NUXIVA_DISPLAY_SOCKET", "/run/nuxiva/display/display.sock"))
LIMIT = 1024 * 1024
TIMEOUT = 2.0
MAX_ITEMS = 64
ID_RE = re.compile(r"^[A-Za-z0-9_.:@-]{1,96}$")
log = logging.getLogger("nuxiva.display.lifecycle")


class EngineUnavailable(RuntimeError):
    pass


class EngineRejected(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class DisplayEngine:

    def __init__(self, socket_path: Path = SOCKET, timeout: float = TIMEOUT) -> None:
        self.socket_path = socket_path
        self.timeout = timeout

    async def call(self, op: str, **fields) -> dict:
        payload = json.dumps({"op": op, **fields}, ensure_ascii=False).encode() + b"\n"
        if len(payload) > LIMIT:
            raise EngineRejected("display.too_large")
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_unix_connection(str(self.socket_path), limit=LIMIT),
                                                    self.timeout)
        except (OSError, asyncio.TimeoutError) as exc:
            raise EngineUnavailable(type(exc).__name__) from exc
        try:
            writer.write(payload)
            await asyncio.wait_for(writer.drain(), self.timeout)
            line = await asyncio.wait_for(reader.readline(), self.timeout)
        except (OSError, asyncio.TimeoutError, ValueError) as exc:
            raise EngineUnavailable(type(exc).__name__) from exc
        finally:
            writer.close()
        reply = json.loads(line or b"{}")
        if not reply.get("ok"):
            raise EngineRejected(str(reply.get("error") or "display.internal"))
        return reply.get("data") or {}


def _cadence(refresh) -> str:
    try:
        value = float(refresh)
    except (TypeError, ValueError):
        return "static"
    if value <= 0:
        return "static"
    if value < 1:
        return "realtime"
    if value <= 2:
        return "live"
    return "fresh" if value <= 60 else "slow"


def clean_report(body: dict) -> dict:
    if not isinstance(body, dict):
        raise ValueError("display.bad_request")
    screen = body.get("screen", 0)
    if not isinstance(screen, int) or not 0 <= screen <= 16:
        raise ValueError("display.bad_request")
    widgets, visible, costs, errors = [], {}, {}, []
    for item in (body.get("widgets") or [])[:MAX_ITEMS]:
        if not isinstance(item, dict):
            continue
        instance, widget = str(item.get("instance") or ""), str(item.get("widget") or "")
        if not (ID_RE.match(instance) and ID_RE.match(widget)):
            continue
        cost = item.get("cost_mb", 0)
        cost = float(cost) if isinstance(cost, (int, float)) and 0 <= cost < 4096 else 0.0
        widgets.append({"instance": instance, "widget": widget, "cadence": _cadence(item.get("refresh")), "cost_mb": cost})
        visible[instance] = item.get("visible") is True
        if isinstance(item.get("measured_mb"), (int, float)) and 0 <= item["measured_mb"] < 4096:
            costs[instance] = float(item["measured_mb"])
        if item.get("failed") is True:
            errors.append(instance)
    budget = body.get("budget_mb")
    budget = float(budget) if isinstance(budget, (int, float)) and 0 < budget < 65536 else None
    return {"screen": screen, "widgets": widgets, "visible": visible, "costs": costs, "errors": errors,
            "budget_mb": budget, "nucleus_only": body.get("nucleus_only") is True}


async def report(engine: DisplayEngine, body: dict) -> dict:
    data = clean_report(body)
    screen = data["screen"]
    moves: list = []
    moves += (await engine.call("audience", screen=screen, nucleus_only=data["nucleus_only"]))["transitions"]
    moves += (await engine.call("admit", screen=screen, widgets=data["widgets"]))["transitions"]
    for instance, seen in data["visible"].items():
        moves += (await engine.call("visibility", instance=instance, visible=seen)).get("transitions", [])
    for instance, cost in data["costs"].items():
        await engine.call("observe", instance=instance, cost_mb=cost)
    for instance in data["errors"]:
        moves += (await engine.call("error", instance=instance)).get("transitions", [])
    if data["budget_mb"] is not None:
        moves += (await engine.call("pressure", screen=screen, budget_mb=data["budget_mb"]))["transitions"]
    tick = await engine.call("tick")
    moves += tick.get("transitions", [])
    mine = [m for m in moves if m.get("screen") == screen]
    states = {m["instance"]: m["to"] for m in mine}
    due = [d["instance"] for d in tick.get("due", []) if d.get("screen") == screen]
    return {"engine": "rust", "states": states, "due": due}


engine = DisplayEngine()
