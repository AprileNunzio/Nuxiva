import os
import threading
import time

from features.people.vitals import camera as camera_module
from features.people.vitals.camera import camera
from features.people.vitals.consent import consent
from features.people.vitals.live import live
from features.people.vitals.watch_engine import LIMITS, MAX_PEOPLE, PyWatch

DEVICE_FRESH = 120.0
METRICS = tuple(LIMITS)


def engine_class():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return PyWatch
    try:
        import nuxiva_native
    except ImportError:
        return PyWatch
    return getattr(nuxiva_native, "RustVitalWatch", PyWatch)


def _device_values(slug: str, now: float) -> dict:
    return {m: v["value"] for m, v in live.latest(slug, now).items()
            if m in METRICS and v.get("kind") != camera_module.KIND and v.get("age", 1e9) <= DEVICE_FRESH}


def _camera_values(slug: str, now: float) -> dict:
    values = (camera.reading(slug, now) or {}).get("values")
    return dict(values) if isinstance(values, dict) else {}


class Watch:

    def __init__(self, engine=None) -> None:
        self._engine = engine if engine is not None else engine_class()()
        self._lock = threading.Lock()

    def _present(self, visible: list, now: float) -> list[str]:
        present = []
        for p in visible:
            slug = p.get("slug") if isinstance(p, dict) else None
            if p.get("known") and isinstance(slug, str) and slug not in present and consent.allowed(slug, now):
                present.append(slug)
            if len(present) >= MAX_PEOPLE:
                break
        return present

    def tick(self, visible: list, now: float | None = None) -> list[dict]:
        now = now or time.time()
        seen = [{"slug": s, "device": _device_values(s, now), "camera": _camera_values(s, now)} for s in self._present(visible, now)]
        with self._lock:
            shown, force = self._engine.tick(seen, camera_module.enabled(), now)
        for slug, seconds in force:
            camera.force(slug, seconds, now)
        return [{**row, "values": {k: int(v) for k, v in row["values"].items()}} for row in shown]

    def forget(self, slug: str) -> None:
        with self._lock:
            known = self._engine.forget(slug)
        if known:
            camera.force(slug, 0)


checkup = Watch()
