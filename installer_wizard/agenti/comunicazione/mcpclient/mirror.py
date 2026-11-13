import asyncio
import concurrent.futures
import contextvars
import functools
import json
import uuid
from pathlib import Path

from config import env_get
from agenti.agent import registry
from agenti.capabilities import schema
from agenti.mcpclient import calls, engine, store

CATALOG = Path(__file__).with_name("areas.json")
CONTEXT = "_context"
TIMEOUT = 600.0
CONTEXTS: dict[str, tuple] = {}
AREAS: dict[str, dict] = {}
ORIGINALS: dict[str, object] = {}


def load() -> None:
    for area in json.loads(CATALOG.read_text(encoding="utf-8"))["areas"]:
        AREAS[area["server"]] = area
        engine.INTERNAL[area["server"]] = functools.partial(definition, area["server"])
        engine.HANDLERS[area["server"]] = functools.partial(handle, area["server"])


def active(server: str) -> bool:
    return env_get(AREAS[server]["flag"], "legacy").lower() == "mcp" and engine.available()


def definition(server: str) -> dict | None:
    tools = []
    for name, traits in AREAS[server]["tools"].items():
        row = registry.TOOLS.get(name)
        if row is None:
            continue
        tools.append({"name": name, "description": row["description"], "input_schema": schema.input_schema(name),
                      "read_only": bool(traits.get("read_only")), "destructive": bool(traits.get("destructive")),
                      "open_world": bool(traits.get("open_world"))})
    return {"id": server, "kind": "mirror", "config": {"tools": tools}} if tools else None


def handle(server: str, tool: str, arguments: str, token: str | None) -> str:
    entry = CONTEXTS.get(token or "")
    if entry is None:
        return json.dumps({"text": "contesto della richiesta non disponibile", "is_error": True})
    loop, context = entry
    done: concurrent.futures.Future = concurrent.futures.Future()

    def start() -> None:
        task = loop.create_task(ORIGINALS[tool](**json.loads(arguments)))
        task.add_done_callback(finish)

    def finish(task: asyncio.Task) -> None:
        if task.cancelled():
            done.set_exception(RuntimeError("operazione annullata"))
        elif task.exception() is not None:
            done.set_exception(task.exception())
        else:
            done.set_result(task.result())

    loop.call_soon_threadsafe(start, context=context)
    try:
        return json.dumps({"text": str(done.result(TIMEOUT)), "is_error": False})
    except Exception as exc:
        return json.dumps({"text": str(exc) or type(exc).__name__, "is_error": True})


def ensure() -> None:
    if not engine.published():
        engine.publish(store.load())


async def route(server: str, name: str, arguments: dict) -> str:
    token = uuid.uuid4().hex
    CONTEXTS[token] = (asyncio.get_running_loop(), contextvars.copy_context())
    tool_id = f"{server}.{name}"
    try:
        await asyncio.to_thread(ensure)
        if not await asyncio.to_thread(engine.wait_tool, tool_id):
            raise RuntimeError(f"il server «{server}» non è disponibile")
        out = (await asyncio.to_thread(calls.invoke, tool_id, {**arguments, CONTEXT: token}, calls.operation(), server))["external"]
    finally:
        CONTEXTS.pop(token, None)
    if out["is_error"]:
        raise RuntimeError(out["text"])
    return out["text"]


def consent(server: str, name: str, previous):
    def check() -> bool:
        if previous and previous():
            return True
        if not active(server):
            return False
        ensure()
        return calls.confirm(f"{server}.{name}")
    return check


def install() -> None:
    for server, area in AREAS.items():
        for name in area["tools"]:
            row = registry.TOOLS.get(name)
            if row is None or name in ORIGINALS:
                continue
            original = row["fn"]
            ORIGINALS[name] = original

            @functools.wraps(original)
            async def routed(*args, _server=server, _name=name, _original=original, **kwargs):
                if not active(_server):
                    return await _original(*args, **kwargs)
                return await route(_server, _name, kwargs)

            row["fn"] = routed
            row["consent"] = consent(server, name, row.get("consent"))


load()
