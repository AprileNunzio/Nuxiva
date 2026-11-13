import asyncio

from config import env_get
from agenti.agent import paths
from agenti.mcpclient import calls, engine, store

SERVER = "files"
AREA = "NUXIVA_MCP_AREA_FILES"
WRITE_BYTES = 64 * 1024 * 1024
DEPTH = 24


def definition() -> dict:
    roots = []
    for name, path in (("work", paths.WORK), ("models", paths.MODELS)):
        path.mkdir(parents=True, exist_ok=True)
        roots.append({"name": name, "path": str(path), "mode": "write", "max_bytes": WRITE_BYTES, "max_depth": DEPTH})
    paths.TRASH.mkdir(parents=True, exist_ok=True)
    return {"id": SERVER, "kind": "filesystem", "config": {"roots": roots, "default_root": "work", "trash": str(paths.TRASH)}}


engine.INTERNAL[SERVER] = definition


def active() -> bool:
    return env_get(AREA, "legacy").lower() == "mcp" and engine.available()


def ensure() -> None:
    if not engine.published():
        engine.publish(store.load())


def needs_consent(tool: str) -> bool:
    if not active():
        return False
    ensure()
    return calls.confirm(f"{SERVER}.{tool}")


def consent(tool: str):
    return lambda: needs_consent(tool)


async def call(tool: str, **arguments) -> str:
    tool_id = f"{SERVER}.{tool}"
    await asyncio.to_thread(ensure)
    if not await asyncio.to_thread(engine.wait_tool, tool_id):
        raise RuntimeError("il server dei file non è disponibile")
    out = (await asyncio.to_thread(calls.invoke, tool_id, arguments, calls.operation(), SERVER))["external"]
    if out["is_error"]:
        raise RuntimeError(out["text"])
    return out["text"]
