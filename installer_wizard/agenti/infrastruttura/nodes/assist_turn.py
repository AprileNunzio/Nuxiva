import asyncio
import re

from fastapi import HTTPException

from agenti.chat import turns
from agenti.nodes.assist_stop_store import AssistStopStore


_ID = re.compile(r"[0-9a-f]{32}")
_stops = AssistStopStore()


async def _wait_for_stop(key: str) -> None:
    while not await asyncio.to_thread(_stops.contains, key):
        await asyncio.sleep(0.25)


def _key(node_id, value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise HTTPException(422, "invalid_turn_id")
    return f"node:{node_id}:{value}"


async def run(node_id, value, operation):
    if value is None:
        return await operation()
    key = _key(node_id, value)
    principal = ("node", node_id)
    if await asyncio.to_thread(_stops.contains, key):
        return {"cancelled": True}
    if turns.controllable(key, principal):
        raise HTTPException(409, "turn_in_progress")
    token = turns.owner.set(principal)
    try:
        with turns.running(key) as turn:
            work = asyncio.create_task(operation())
            watcher = asyncio.create_task(_wait_for_stop(key))
            try:
                done, _ = await asyncio.wait((work, watcher), return_when=asyncio.FIRST_COMPLETED)
                if watcher in done:
                    watcher.result()
                    return {"cancelled": True}
                return work.result()
            except asyncio.CancelledError:
                if not turn.stopping:
                    raise
                return {"cancelled": True}
            finally:
                for task in (work, watcher):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(work, watcher, return_exceptions=True)
    finally:
        turns.owner.reset(token)


async def stop(node_id, value):
    key = _key(node_id, value)
    await asyncio.to_thread(_stops.record, key)
    return turns.stop(key, ("node", node_id))
