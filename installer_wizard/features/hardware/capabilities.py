from __future__ import annotations

from typing import Dict, Iterable, List

CATEGORY_CAPABILITY: Dict[str, str] = {
    "wifi": "network.wifi",
    "network": "network.ethernet",
    "bluetooth": "bluetooth.controller",
    "gpu": "graphics.render",
    "audio": "audio.io",
    "camera": "media.capture",
    "serial": "serial.port",
    "printer": "print.spooler",
    "storage": "storage.removable",
    "input": "input.hid",
    "cellular": "network.cellular",
}


def capabilities_for(category: str, status: str, extra: Iterable[str] = ()) -> List[str]:

    if status != "ready":
        return []
    caps: List[str] = []
    base = CATEGORY_CAPABILITY.get(category)
    if base:
        caps.append(base)
    for cap in extra:
        if cap and cap not in caps:
            caps.append(cap)
    return caps


def aggregate(devices: Iterable[object]) -> Dict[str, List[str]]:

    out: Dict[str, List[str]] = {}
    for dev in devices:
        if getattr(dev, "status", "") != "ready":
            continue
        for cap in getattr(dev, "capabilities", []) or []:
            out.setdefault(cap, []).append(getattr(dev, "id", ""))
    return out
