import threading
import time

from features.people.vitals import camera as camera_module
from features.people.vitals.book import book
from features.people.vitals.camera import camera
from features.people.vitals.live import live

GREET_SECONDS = 2.5
DEVICE_WAIT = 25.0
HOLD_SECONDS = 20.0
BREATH_WAIT = 45.0
GIVE_UP = 70.0
SHOW_DONE = 25.0
SHOW_FAILED = 12.0
COOLDOWN = 30 * 60.0
AWAY_GRACE = 8.0
RETRY_AFTER_LEAVE = 60.0
MOVED_DROP = 0.25
MOVED_SHOW = 3.0
DEVICE_FRESH = 120.0
METRICS = ("heart_rate", "resp_rate")


def _device_rows(slug: str) -> list[dict]:
    return [{"label": str(d.get("label", ""))[:40], "kind": d.get("kind", "")} for d in book.of(slug) if d.get("enabled", True)][:3]


def _device_values(slug: str, since: float, now: float) -> dict:
    out = {}
    for metric, value in live.latest(slug, now).items():
        if metric in METRICS and value.get("kind") != camera_module.KIND and (value["ts"] >= since or value.get("age", 1e9) <= DEVICE_FRESH):
            out[metric] = value["value"]
    return out


class Checkup:

    def __init__(self) -> None:
        self._runs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _start(self, slug: str, now: float) -> dict:
        devices = _device_rows(slug)
        run = {"id": f"{slug}-{int(now)}", "slug": slug, "started": now, "phase": "greet", "phase_at": now, "devices": devices,
               "values": {}, "source": "", "progress": 0.0, "moved_at": 0.0, "hold_from": 0.0, "last_near": now, "ended": 0.0}
        self._runs[slug] = run
        return run

    @staticmethod
    def _enter(run: dict, phase: str, now: float) -> None:
        run["phase"], run["phase_at"] = phase, now
        if phase == "camera":
            run["hold_from"] = now
            camera.force(run["slug"], GIVE_UP, now)
        if phase in ("done", "failed"):
            run["ended"] = now
            camera.force(run["slug"], 0, now)

    def _device_step(self, run: dict, now: float) -> None:
        found = _device_values(run["slug"], run["started"], now)
        if found.get("heart_rate"):
            run["values"], run["source"] = found, "device"
            self._enter(run, "done", now)
        elif now - run["phase_at"] >= DEVICE_WAIT:
            self._enter(run, "camera" if camera_module.enabled() else "failed", now)

    def _camera_step(self, run: dict, now: float) -> None:
        reading = camera.reading(run["slug"], now) or {}
        progress = float(reading.get("progress") or 0.0)
        if run["progress"] - progress >= MOVED_DROP:
            run["moved_at"], run["hold_from"] = now, now
        run["progress"] = progress
        for metric, value in (reading.get("values") or {}).items():
            if metric in METRICS:
                run["values"][metric] = value
        run["source"] = "camera"
        elapsed = now - run["phase_at"]
        if run["values"].get("heart_rate") and (run["values"].get("resp_rate") or elapsed >= BREATH_WAIT):
            self._enter(run, "done", now)
        elif elapsed >= GIVE_UP or not camera_module.enabled():
            self._enter(run, "done" if run["values"].get("heart_rate") else "failed", now)

    def _advance(self, run: dict, now: float) -> None:
        if run["phase"] == "greet" and now - run["phase_at"] >= GREET_SECONDS:
            self._enter(run, "device" if run["devices"] else "camera", now)
        elif run["phase"] == "device":
            self._device_step(run, now)
        elif run["phase"] == "camera":
            self._camera_step(run, now)

    def _possible(self, slug: str) -> bool:
        return camera_module.enabled() or bool(_device_rows(slug))

    def tick(self, slug: str, near: bool, now: float | None = None) -> dict | None:
        now = now or time.time()
        with self._lock:
            run = self._runs.get(slug)
            if run and run["ended"]:
                shown = SHOW_DONE if run["phase"] == "done" else SHOW_FAILED
                if now - run["ended"] < shown:
                    return self.view(run, now)
                if now - run["ended"] < COOLDOWN:
                    return None
                run = None
            if run and not near:
                if now - run["last_near"] > AWAY_GRACE:
                    camera.force(slug, 0, now)
                    run.update(ended=now - COOLDOWN + RETRY_AFTER_LEAVE, phase="left")
                    return None
                return self.view(run, now)
            if not near or not self._possible(slug):
                return None
            run = run or self._start(slug, now)
            run["last_near"] = now
            self._advance(run, now)
            return self.view(run, now)

    @staticmethod
    def view(run: dict, now: float) -> dict:
        phase = run["phase"]
        hold_left = max(0, int(round(HOLD_SECONDS - (now - run["hold_from"])))) if phase == "camera" else 0
        if phase == "camera":
            progress = max(min(1.0, (now - run["hold_from"]) / HOLD_SECONDS) * 0.6 + run["progress"] * 0.4, 0.0)
        elif phase == "device":
            progress = min(1.0, (now - run["phase_at"]) / DEVICE_WAIT)
        else:
            progress = 1.0 if phase == "done" else 0.0
        return {"session": run["id"], "phase": phase, "devices": run["devices"], "values": dict(run["values"]), "source": run["source"],
                "hold_left": hold_left, "progress": round(min(1.0, progress), 3), "moved": phase == "camera" and now - run["moved_at"] <= MOVED_SHOW,
                "elapsed": int(now - run["phase_at"])}


checkup = Checkup()
