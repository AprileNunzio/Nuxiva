from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, Optional

LOCAL_COMMANDS: Dict[str, tuple] = {
    "reboot": ("systemctl", "reboot"),
    "restart": ("systemctl", "restart", "nuxiva-supervisor"),
}
SETUP = "setup"
DESTRUCTIVE: FrozenSet[str] = frozenset({"reboot", "restart", "update", SETUP})


class NodeCommandError(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class NodeControl:
    node_id: str
    scope: str
    commands: tuple


def _paired_registry():
    from features.nodes.registry import COMMANDS, registry

    return registry, COMMANDS


def describe(node_id: str, local_id: str, registry_loader: Callable = _paired_registry) -> NodeControl:
    if node_id == local_id:
        commands = tuple(LOCAL_COMMANDS) if os.name == "posix" else ()
        return NodeControl(node_id, "local", (*commands, SETUP))
    registry, paired_commands = registry_loader()
    if node_id in registry.data.get("nodes", {}):
        return NodeControl(node_id, "paired", tuple(paired_commands))
    return NodeControl(node_id, "mesh", ())


def execute(
    control: NodeControl,
    command: str,
    confirmed: bool,
    schedule_local: Callable[[tuple], None],
    registry_loader: Callable = _paired_registry,
    reopen_setup: Optional[Callable[[], None]] = None,
) -> Dict[str, str]:
    if command not in control.commands:
        raise NodeCommandError("command_not_available", 409)
    if command in DESTRUCTIVE and not confirmed:
        raise NodeCommandError("confirmation_required", 428)
    if control.scope == "local" and command == SETUP:
        if reopen_setup is None:
            raise NodeCommandError("command_not_available", 409)
        reopen_setup()
        return {"node_id": control.node_id, "command": command, "status": "executing"}
    if control.scope == "local":
        schedule_local(LOCAL_COMMANDS[command])
        return {"node_id": control.node_id, "command": command, "status": "executing"}
    registry, _ = registry_loader()
    registry.command(control.node_id, command)
    return {"node_id": control.node_id, "command": command, "status": "queued"}


def control_payload(control: NodeControl, online: Optional[bool]) -> Dict[str, object]:
    return {"node_id": control.node_id, "scope": control.scope, "commands": list(control.commands), "online": online}
