import re

DEVICE_ID_RE = re.compile(r"^[0-9A-Za-z\-]{1,8}:[0-9A-Za-z\-]{1,8}@[\w.:\-]{1,80}$")


def _nodes(device: dict) -> set[str]:
    return {n for n in (device.get("rgb"), device.get("ir"), *(device.get("meta") or [])) if n}


def owners(device: dict, items: dict) -> list[dict]:
    nodes = _nodes(device)
    found = [c for c in items.values() if c.get("kind") == "webcam"
             and (c.get("device_id") == device.get("id") or (not c.get("device_id") and (c.get("url") in nodes or c.get("node") in nodes)))]
    return sorted(found, key=lambda c: c.get("created", 0))


def plan(devices: list[dict], items: dict, busy: set[str]) -> dict:
    add, update, remove = [], [], []
    for device in devices:
        rgb, device_id = device.get("rgb"), str(device.get("id") or "")
        if not rgb or not DEVICE_ID_RE.fullmatch(device_id):
            continue
        found = owners(device, items)
        if not found:
            if rgb not in busy:
                add.append({"name": str(device.get("name") or "Webcam").strip()[:40] or "Webcam", "kind": "webcam", "url": rgb,
                            "node": rgb, "device_id": device_id, "retention_min": 60, "enabled": True, "record": True, "consent": True})
            continue
        keep, extra = found[0], found[1:]
        if keep.get("device_id") != device_id or keep.get("url") != rgb or keep.get("node") != rgb:
            update.append((keep["id"], {"device_id": device_id, "url": rgb, "node": rgb}))
        remove.extend(c["id"] for c in extra)
    return {"add": add, "update": update, "remove": remove}


def busy_reason(cam: dict, busy: set[str]) -> str:
    if cam.get("kind") == "webcam" and (cam.get("url") in busy or cam.get("node") in busy):
        return "in_use_by_vision"
    return ""
