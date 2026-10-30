import asyncio
import hashlib
import json
import logging
import pwd
import re

from features.bluetooth import store
from features.devices.audio import KIOSK_USER

log = logging.getLogger("nuxiva.bluetooth")
LINE = re.compile(r"^[^\w]*(?P<name>.+?)\s+id=(?P<id>\d+)\s+\[slave\s+(?P<kind>pointer|keyboard)", re.M)
TOOLS = {"xinput", "setxkbmap"}


async def _x(tool: str, *args: str) -> tuple[int, str]:
    if tool not in TOOLS:
        raise ValueError("bluetooth_tool_not_allowed")
    try:
        home = pwd.getpwnam(KIOSK_USER).pw_dir
    except KeyError:
        return 1, "kiosk user missing"
    try:
        proc = await asyncio.create_subprocess_exec(
            "runuser", "-u", KIOSK_USER, "--", "env", "DISPLAY=:0", f"XAUTHORITY={home}/.Xauthority", "LC_ALL=C",
            tool, *args, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT)
    except OSError as exc:
        return 127, str(exc)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), 6)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "timeout"
    return proc.returncode or 0, out.decode("utf-8", "replace")


def _matches(xname: str, name: str) -> bool:
    return xname == name or xname.startswith(f"{name} ")


def _commands(dev: dict, settings: dict, inputs: list[tuple[str, str, str]]) -> list[tuple[str, ...]]:
    commands: list[tuple[str, ...]] = []
    for xname, xid, kind in inputs:
        if not _matches(xname, dev["name"]):
            continue
        if kind == "pointer" and "pointer" in dev["capabilities"]:
            speed = f"{max(-10, min(10, int(settings['pointer_speed']))) / 10:.1f}"
            commands += [("xinput", "set-prop", xid, "libinput Accel Speed", speed),
                         ("xinput", "set-prop", xid, "libinput Natural Scrolling Enabled",
                          "1" if settings["natural_scroll"] else "0"),
                         ("xinput", "set-prop", xid, "libinput Left Handed Enabled",
                          "1" if settings["left_handed"] else "0")]
        if kind == "keyboard" and "keyboard" in dev["capabilities"] and settings["keyboard_layout"] != "auto":
            commands.append(("setxkbmap", "-device", xid, "-layout", settings["keyboard_layout"]))
    return commands


class HidApplier:
    def __init__(self) -> None:
        self.signature = ""

    async def apply(self, devs: list[dict]) -> int:
        live = [d for d in devs if d["connected"] and {"pointer", "keyboard"} & set(d["capabilities"])]
        if not live:
            self.signature = ""
            return 0
        code, listing = await _x("xinput", "list")
        if code != 0:
            return 0
        inputs = [(m["name"].strip(), m["id"], m["kind"]) for m in LINE.finditer(listing)]
        data = store.load()
        plan = [cmd for d in live for cmd in _commands(d, store.settings(data, d["mac"]), inputs)]
        signature = hashlib.sha256(json.dumps(plan).encode()).hexdigest()
        if signature == self.signature:
            return 0
        failures = 0
        for tool, *args in plan:
            rc, out = await _x(tool, *args)
            if rc != 0:
                failures += 1
                log.warning("Impostazione periferica non applicata (%s): %s", tool, out.strip()[:160])
        self.signature = signature
        return len(plan) - failures


hid = HidApplier()
