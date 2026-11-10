import asyncio
import re

from fastapi import HTTPException

from features.chat import turns


_ID = re.compile(r"[0-9a-f]{32}")


def _key(node_id, value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise HTTPException(422, "invalid_turn_id")
    return f"node:{node_id}:{value}"


async def run(node_id, value, operation):
    if value is None:
        return await operation()
    key = _key(node_id, value)
    principal = ("node", node_id)
    if turns.controllable(key, principal):
        raise HTTPException(409, "turn_in_progress")
    token = turns.owner.set(principal)
    try:
        with turns.running(key) as turn:
            try:
                result = await operation()
            except asyncio.CancelledError:
                if not turn.stopping:
                    raise
                return {"cancelled": True}
            return {"cancelled": True} if turn.stopping else result
    finally:
        turns.owner.reset(token)


def stop(node_id, value):
    return turns.stop(_key(node_id, value), ("node", node_id))
