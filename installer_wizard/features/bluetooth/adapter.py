import asyncio
import re
import shutil
from pathlib import Path

MAC_RE = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")
SYS_BT = Path("/sys/class/bluetooth")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x01|\x02")
SCAN_MIN, SCAN_MAX = 5, 60


class BluetoothError(RuntimeError):
    pass


def valid_mac(mac: str) -> str:
    mac = str(mac or "").strip().upper()
    if not MAC_RE.match(mac):
        raise ValueError("bluetooth_invalid_mac")
    return mac


def has_adapter() -> bool:
    return any(SYS_BT.glob("hci*"))


def installed() -> bool:
    return shutil.which("bluetoothctl") is not None


async def ctl(*args: str, timeout: float = 15) -> tuple[int, str]:
    try:
        proc = await asyncio.create_subprocess_exec("bluetoothctl", *args, stdin=asyncio.subprocess.DEVNULL,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    except OSError as exc:
        raise BluetoothError(f"bluetoothctl: {exc}") from exc
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "timeout"
    return proc.returncode or 0, ANSI.sub("", out.decode("utf-8", "replace"))


def _field(text: str, name: str) -> str:
    match = re.search(rf"^\s*{re.escape(name)}:\s*(.+)$", text, re.M)
    return match.group(1).strip() if match else ""


def _int(text: str, base: int = 10) -> int | None:
    try:
        return int(text.split()[0], base) if text else None
    except (ValueError, IndexError):
        return None


def parse_info(mac: str, text: str) -> dict:
    battery = re.search(r"Battery Percentage:.*\((\d+)\)", text)
    rssi = re.search(r"RSSI:\s*(?:0x[0-9a-fA-F]+\s*\()?(-?\d+)", text)
    name = _field(text, "Alias") or _field(text, "Name") or mac
    return {
        "mac": mac,
        "name": "".join(ch for ch in name if ch.isprintable())[:80] or mac,
        "icon": _field(text, "Icon")[:40],
        "cod": _int(_field(text, "Class"), 16),
        "appearance": _int(_field(text, "Appearance"), 16),
        "paired": _field(text, "Paired") == "yes",
        "bonded": _field(text, "Bonded") == "yes",
        "trusted": _field(text, "Trusted") == "yes",
        "blocked": _field(text, "Blocked") == "yes",
        "connected": _field(text, "Connected") == "yes",
        "battery": min(100, int(battery.group(1))) if battery else None,
        "rssi": int(rssi.group(1)) if rssi else None,
        "uuids": sorted({u[:8].lower() for u in re.findall(r"UUID:.*\(([0-9a-fA-F-]{36})\)", text)}),
    }


async def controller() -> dict:
    base = {"present": has_adapter(), "installed": installed(), "powered": False, "discovering": False,
            "pairable": False, "name": "", "address": ""}
    if not base["present"] or not base["installed"]:
        return base
    _, out = await ctl("show")
    address = re.search(r"Controller ([0-9A-F:]{17})", out)
    return {**base, "powered": _field(out, "Powered") == "yes", "discovering": _field(out, "Discovering") == "yes",
            "pairable": _field(out, "Pairable") == "yes", "name": (_field(out, "Alias") or _field(out, "Name"))[:80],
            "address": address.group(1) if address else ""}


async def devices() -> list[dict]:
    _, out = await ctl("devices")
    macs = list(dict.fromkeys(re.findall(r"^Device ([0-9A-F:]{17})", out, re.M)))[:64]
    infos = await asyncio.gather(*(ctl("info", mac) for mac in macs))
    return [parse_info(mac, text) for mac, (_, text) in zip(macs, infos)]


async def _run(*args: str, timeout: float = 30, ok: tuple[str, ...] = ()) -> str:
    code, out = await ctl(*args, timeout=timeout)
    if code != 0 or (ok and not any(token in out for token in ok)):
        tail = out.strip().splitlines()[-1] if out.strip() else f"code {code}"
        raise BluetoothError(tail[:200])
    return out


async def power(on: bool) -> None:
    await _run("power", "on" if on else "off", ok=("succeeded",))


async def scan(seconds: int) -> None:
    seconds = max(SCAN_MIN, min(SCAN_MAX, int(seconds)))
    await ctl("--timeout", str(seconds), "scan", "on", timeout=seconds + 10)


async def pair(mac: str) -> None:
    mac = valid_mac(mac)
    await ctl("pairable", "on")
    code, out = await ctl("--agent=NoInputNoOutput", "pair", mac, timeout=45)
    failed = code != 0 or "Failed to pair" in out
    if failed and "AlreadyExists" not in out:
        tail = out.strip().splitlines()[-1] if out.strip() else f"code {code}"
        raise BluetoothError(tail[:200])
    await trust(mac)


async def trust(mac: str) -> None:
    await _run("trust", valid_mac(mac), ok=("succeeded",))


async def untrust(mac: str) -> None:
    await _run("untrust", valid_mac(mac), ok=("succeeded",))


async def connect(mac: str) -> None:
    await _run("connect", valid_mac(mac), timeout=30, ok=("Connection successful", "AlreadyConnected"))


async def disconnect(mac: str) -> None:
    await _run("disconnect", valid_mac(mac), ok=("Successful", "succeeded", "Not Connected"))


async def forget(mac: str) -> None:
    await _run("remove", valid_mac(mac))
