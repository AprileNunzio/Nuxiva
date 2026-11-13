from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from collections import deque
from datetime import datetime

from resource_actions import loaded_models, release_heap, trimmers, unload_model
from resource_plan import plan
from resource_probe import groups, system_sample

log = logging.getLogger("nuxiva.resources")

INTERVAL = 5.0
CLIENT_TTL = 90.0
MAX_DEVICES = 16
MAX_SURFACES = 64
KEEPALIVE_S = 300.0
ID_RE = re.compile(r"^[a-z0-9_.:-]{1,64}$")
DEVICE_RE = re.compile(r"^[A-Za-z0-9_-]{6,40}$")
PROTECTED_SURFACES = frozenset({"voice", "rescue", "defense-alert", "captions"})
PROCESS_CLASS = {"nuxiva-core": ("protected", False), "ollama": ("high", False), "browser": ("normal", False), "media": ("high", False)}


def _expiry_idle_s(raw: object) -> float:
    if not isinstance(raw, str):
        return 0.0
    try:
        remaining = datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp() - time.time()
    except ValueError:
        return 0.0
    return max(0.0, KEEPALIVE_S - max(0.0, remaining))


def device_scale(cores: int, memory_gb: float) -> float:
    if memory_gb >= 8 and cores >= 8:
        return 4.0
    if memory_gb >= 4 and cores >= 4:
        return 2.0
    if memory_gb >= 2 or (memory_gb == 0 and cores >= 4):
        return 1.0
    return 0.5


def clean_report(body: object) -> dict | None:
    if not isinstance(body, dict) or not DEVICE_RE.fullmatch(str(body.get("device", ""))):
        return None
    surfaces = []
    for item in (body.get("surfaces") or [])[:MAX_SURFACES]:
        if not isinstance(item, dict):
            continue
        ident = str(item.get("id", "")).lower()
        mb = item.get("mb")
        if not ID_RE.fullmatch(ident) or isinstance(mb, bool) or not isinstance(mb, (int, float)) or not 0 <= mb <= 65536:
            continue
        surfaces.append({"id": ident, "mb": float(mb), "visible": item.get("visible") is True,
                         "idle_ms": int(min(max(float(item.get("idle_ms") or 0), 0), 86_400_000))})
    cores, memory = body.get("cores", 0), body.get("device_memory", 0)
    cores = int(cores) if isinstance(cores, (int, float)) and not isinstance(cores, bool) and 0 <= cores <= 256 else 0
    memory = float(memory) if isinstance(memory, (int, float)) and not isinstance(memory, bool) and 0 <= memory <= 1024 else 0.0
    heap = body.get("js_heap_mb", 0)
    heap = float(heap) if isinstance(heap, (int, float)) and not isinstance(heap, bool) and 0 <= heap <= 65536 else 0.0
    return {"device": body["device"], "surfaces": surfaces, "js_heap_mb": heap, "scale": device_scale(cores, memory), "at": time.monotonic()}


class ResourceManager:
    def __init__(self) -> None:
        self.pid = os.getpid()
        self.level: str | None = None
        self.last: dict = {}
        self.clients: dict[str, dict] = {}
        self.history: deque = deque(maxlen=180)
        self.log: deque = deque(maxlen=200)

    def collect(self) -> list[dict]:
        components = []
        for key, entry in groups(self.pid).items():
            cls, reclaim = PROCESS_CLASS[key]
            components.append({"id": key, "kind": "process", "class": cls, "rss": entry["rss"], "idle_ms": 0,
                               "visible": True, "reclaimable": reclaim, "cpu_percent": min(entry["cpu_percent"], 100.0 * 64)})
        for model in loaded_models():
            ident = re.sub(r"[^A-Za-z0-9_.:/-]", "", model["name"])[:120]
            size = model.get("size")
            components.append({"id": f"model.{re.sub(r'[^a-z0-9_.-]', '-', ident.lower())[:56]}", "kind": "model", "class": "normal",
                               "rss": int(size) if isinstance(size, int) and size >= 0 else 0,
                               "idle_ms": int(_expiry_idle_s(model.get("expires_at")) * 1000), "visible": False, "reclaimable": True,
                               "_name": ident})
        components.extend(trimmers.components())
        now = time.monotonic()
        for device in [d for d, c in self.clients.items() if now - c["at"] > CLIENT_TTL]:
            del self.clients[device]
        for device, client in self.clients.items():
            for s in client["surfaces"]:
                cls = "protected" if s["id"] in PROTECTED_SURFACES else "normal"
                components.append({"id": f"{device[:12].lower()}.{s['id']}"[:64], "kind": "surface", "class": cls,
                                   "rss": int(s["mb"] * 1048576), "idle_ms": int(s["idle_ms"] / client["scale"]), "visible": s["visible"],
                                   "reclaimable": True, "_device": device, "_surface": s["id"]})
        return components

    def evaluate(self) -> dict:
        components = self.collect()
        names = {c["id"]: c["_name"] for c in components if "_name" in c}
        payload = {"system": system_sample(), "previous": self.level,
                   "components": [{k: v for k, v in c.items() if not k.startswith("_")} for c in components]}
        result = plan(payload)
        self.level = result["level"]
        by_id = {c["id"]: c for c in components}
        done = []
        for action in result["actions"]:
            comp = by_id.get(action["id"])
            if comp is None or comp["class"] == "protected":
                continue
            ok = self.execute(action, comp, names)
            done.append({**action, "ok": ok})
        if result["level"] != "calm":
            release_heap()
        self.last = {**result, "at": time.time(), "applied": done, "system": payload["system"],
                     "components": [{"id": c["id"], "kind": c["kind"], "class": c["class"], "rss": c["rss"], "visible": c["visible"]} for c in components],
                     "directives": self.directives(result, by_id)}
        self.history.append({"at": self.last["at"], "level": result["level"], "pressure": result["pressure"], "mem_percent": result["mem_percent"]})
        for item in done:
            self.log.append({"at": self.last["at"], **item})
        return self.last

    def execute(self, action: dict, comp: dict, names: dict) -> bool:
        kind = action["action"]
        if kind == "unload" and comp["kind"] == "model":
            return unload_model(names.get(action["id"], ""))
        if kind in ("trim", "drop") and comp["kind"] == "cache":
            return trimmers.run(action["id"])
        if kind in ("suspend", "hibernate") and comp["kind"] == "surface":
            return True
        return False

    def directives(self, result: dict, by_id: dict) -> dict:
        out: dict[str, dict] = {}
        for action in result["actions"]:
            comp = by_id.get(action["id"])
            if comp is None or comp["kind"] != "surface" or action["action"] not in ("suspend", "hibernate"):
                continue
            slot = out.setdefault(comp["_device"], {"suspend": [], "hibernate": []})
            slot[action["action"]].append(comp["_surface"])
        return out

    def report(self, clean: dict) -> dict:
        if clean["device"] not in self.clients and len(self.clients) >= MAX_DEVICES:
            oldest = min(self.clients, key=lambda d: self.clients[d]["at"])
            del self.clients[oldest]
        self.clients[clean["device"]] = clean
        return self.directive_for(clean["device"])

    def directive_for(self, device: str) -> dict:
        slot = (self.last.get("directives") or {}).get(device, {"suspend": [], "hibernate": []})
        return {"level": self.last.get("level", "calm"), "suspend": slot["suspend"], "hibernate": slot["hibernate"]}

    def snapshot(self) -> dict:
        return {"state": {k: v for k, v in self.last.items() if k != "directives"}, "history": list(self.history), "log": list(self.log)[-50:]}

    async def run(self, interval: float = INTERVAL) -> None:
        while True:
            try:
                await asyncio.to_thread(self.evaluate)
            except (OSError, ValueError, RuntimeError) as exc:
                log.error("Ciclo risorse non riuscito: %s", exc)
            await asyncio.sleep(interval)


resource_manager = ResourceManager()
