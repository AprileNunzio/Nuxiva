import secrets
import threading
import time

MODES = ("particles", "realistic", "anatomy")
VIEW = ("zoom_in", "zoom_out", "rotate_left", "rotate_right", "rotate_up", "rotate_down", "reset", "explode", "collapse",
        "animate", "still")
TTL_SECONDS = 600.0
SUBJECT_MAX = 64
FINAL = ("designed", "exact")


class Session:

    def __init__(self, clock=time.time) -> None:
        self.clock = clock
        self.lock = threading.Lock()
        self.data = self._empty()

    @staticmethod
    def _empty() -> dict:
        return {"id": "", "subject": "", "mode": "particles", "status": "idle", "source": "", "reason": "", "scene": None,
                "command": {"seq": 0, "name": ""}, "animate": True, "until": 0.0, "updated_at": 0.0}

    def _touch(self) -> None:
        now = self.clock()
        self.data["until"] = now + TTL_SECONDS
        self.data["updated_at"] = round(now, 3)

    def begin(self, subject: str, mode: str = "particles") -> str:
        with self.lock:
            seq = self.data["command"]["seq"]
            self.data = self._empty()
            self.data.update(id=secrets.token_hex(8), subject=str(subject or "").strip()[:SUBJECT_MAX],
                             mode=mode if mode in MODES else "particles", status="building", command={"seq": seq, "name": ""})
            self._touch()
            return self.data["id"]

    def scene_ready(self, session_id: str, scene: dict, source: str) -> bool:
        with self.lock:
            if session_id != self.data["id"] or (self.data["source"] in FINAL and source not in FINAL):
                return False
            self.data.update(scene=scene, source=source, status="ready" if source in FINAL else "refining", reason="")
            self.data["updated_at"] = round(self.clock(), 3)
            return True

    def failed(self, session_id: str, reason: str) -> None:
        with self.lock:
            if session_id != self.data["id"]:
                return
            self.data.update(status="draft_only" if self.data["scene"] else "failed", reason=str(reason)[:80])
            self.data["updated_at"] = round(self.clock(), 3)

    def active(self) -> bool:
        with self.lock:
            return bool(self.data["id"]) and self.data["until"] > self.clock()

    def set_mode(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"holo_bad_mode:{mode}")
        with self.lock:
            self.data["mode"] = mode
            self._touch()

    def command(self, name: str) -> None:
        if name not in VIEW:
            raise ValueError(f"holo_bad_command:{name}")
        with self.lock:
            if name in ("animate", "still"):
                self.data["animate"] = name == "animate"
            self.data["command"] = {"seq": self.data["command"]["seq"] + 1, "name": name}
            self._touch()

    def close(self) -> None:
        with self.lock:
            seq = self.data["command"]["seq"]
            self.data = self._empty()
            self.data["command"] = {"seq": seq, "name": ""}
            self.data["updated_at"] = round(self.clock(), 3)

    def brief(self) -> dict:
        out = self.snapshot()
        out["scene"] = None
        return out

    def snapshot(self) -> dict:
        with self.lock:
            live = bool(self.data["id"]) and self.data["until"] > self.clock()
            out = {k: v for k, v in self.data.items() if k != "until"}
            out["command"] = dict(self.data["command"])
            out["active"] = live
            if not live:
                out.update(scene=None, mode="particles")
            return out


session = Session()
