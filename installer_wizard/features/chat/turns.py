import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from access import session_user
from features.desktop.display_scope import is_host_display


owner: ContextVar[tuple[str, str] | None] = ContextVar("chat_turn_owner", default=None)


def request_owner(request) -> tuple[str, str] | None:
    if is_host_display(request):
        return ("host", "")
    user = session_user(request) if request.url.scheme == "https" else None
    return ("user", user) if user else None


@dataclass
class Turn:
    owner: tuple[str, str]
    task: asyncio.Task
    stopping: bool = False


_active: dict[str, Turn] = {}


@contextmanager
def running(turn_id: str):
    principal, task = owner.get(), asyncio.current_task()
    turn = Turn(principal, task) if turn_id and principal and task else None
    if turn:
        _active[turn_id] = turn
    try:
        yield turn
    finally:
        if turn:
            _active.pop(turn_id, None)


def controllable(turn_id: str, principal: tuple[str, str] | None) -> bool:
    turn = _active.get(turn_id)
    return bool(turn and turn.owner == principal)


def stop(turn_id: str, principal: tuple[str, str] | None) -> bool:
    if not controllable(turn_id, principal):
        return False
    turn = _active[turn_id]
    if not turn.stopping:
        turn.stopping = True
        turn.task.cancel()
    return True
