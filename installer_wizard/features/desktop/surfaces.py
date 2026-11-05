import json
import logging
import math
import os
import re
import threading
import time
import unicodedata

from config import STATE_DIR

from features.desktop.privacy import flag

log = logging.getLogger("nuxiva.desktop.surfaces")
FILE = STATE_DIR / "display" / "surfaces.json"
ROOM = re.compile(r"^[a-z0-9_-]{1,48}$")
KINDS = frozenset({"monitor", "xr_headset", "holo_quilt", "holo_pyramid", "holo_fan", "cast"})
SIDES = ("left", "right", "up", "down")
INPUTS = ("touch", "pointer", "hands", "gaze", "keyboard")
AUDIENCES = frozenset({"empty", "guest_only", "authorized", "mixed", "uncertain"})
MAX_SCREEN = 16
SENSED_TTL = 10.0
LIMIT_M = 100.0


def _native(name: str):
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, name, None)


def slug(text) -> str:
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", plain).strip("_")[:48]


def strict() -> bool:
    return flag("NUXIVA_DISPLAY_ROOM_STRICT", False)


def _bounded(value, limit: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(-limit, min(limit, number)) if math.isfinite(number) else 0.0


def clean_pose(raw) -> dict | None:
    if not isinstance(raw, dict):
        return None
    room = slug(raw.get("room"))
    if not ROOM.match(room):
        return None
    return {"room": room, "x_m": _bounded(raw.get("x_m"), LIMIT_M), "y_m": _bounded(raw.get("y_m"), LIMIT_M),
            "z_m": _bounded(raw.get("z_m"), LIMIT_M), "yaw_deg": _bounded(raw.get("yaw_deg"), 360.0)}


def _whole(value, lo: int, hi: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, number))


def clean_surface(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    kind = raw.get("kind") if raw.get("kind") in KINDS else "monitor"
    given = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    gpu = raw.get("gpu") if isinstance(raw.get("gpu"), dict) else {}
    return {"kind": kind, "width": _whole(raw.get("width"), 1, 16384, 1920), "height": _whole(raw.get("height"), 1, 16384, 1080),
            "refresh_hz": _whole(raw.get("refresh_hz"), 1, 500, 60), "input": {k: given.get(k) is True for k in INPUTS},
            "gpu": {"webgl2": gpu.get("webgl2") is True, "max_texture": _whole(gpu.get("max_texture"), 0, 65536, 0)}}


class Surfaces:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._poses: dict[int, dict] | None = None
        self._sensed: tuple[float, list[str]] = (0.0, [])

    def poses(self) -> dict[int, dict]:
        with self._lock:
            if self._poses is None:
                self._poses = self._read()
            return dict(self._poses)

    @staticmethod
    def _read() -> dict[int, dict]:
        try:
            raw = json.loads(FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            log.error("Posizioni degli schermi illeggibili, uso la disposizione da sinistra a destra: %s", exc)
            return {}
        out = {}
        for key, value in (raw.items() if isinstance(raw, dict) else ()):
            pose = clean_pose(value)
            if str(key).isdigit() and int(key) <= MAX_SCREEN and pose:
                out[int(key)] = pose
        return out

    def save(self, body) -> dict[int, dict]:
        if not isinstance(body, dict) or len(body) > MAX_SCREEN + 1:
            raise ValueError("invalid_surfaces")
        clean = {}
        for key, value in body.items():
            if not str(key).isdigit() or int(key) > MAX_SCREEN:
                raise ValueError("invalid_screen")
            if value is None:
                continue
            pose = clean_pose(value)
            if pose is None:
                raise ValueError("invalid_pose")
            clean[int(key)] = pose
        FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps({str(k): v for k, v in sorted(clean.items())}, indent=2), encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(FILE)
        with self._lock:
            self._poses = clean
        return clean

    def descriptors(self, active: list[dict]) -> list[dict]:
        poses = self.poses()
        return [{"n": s["n"], "x": s.get("x", 0), "surface": {**clean_surface(s.get("surface")), "placement": poses.get(s["n"])}}
                for s in active]

    @staticmethod
    def _ordered(active: list[dict]) -> dict[str, dict]:
        numbers = [s["n"] for s in active]
        return {str(n): {"room": None, "left": numbers[i - 1] if i else None,
                         "right": numbers[i + 1] if i + 1 < len(numbers) else None, "up": None, "down": None}
                for i, n in enumerate(numbers)}

    def layout(self, active: list[dict]) -> dict[str, dict]:
        engine = _native("surface_layout")
        poses = self.poses()
        if engine is None:
            fallback = self._ordered(active)
            for n, entry in fallback.items():
                entry["room"] = (poses.get(int(n)) or {}).get("room")
            return fallback
        return json.loads(engine(json.dumps(self.descriptors(active))))

    def annotate(self, active: list[dict]) -> list[dict]:
        try:
            placed = self.layout(active)
        except ValueError as exc:
            log.error("Vicini fisici degli schermi non calcolati: %s", exc)
            placed = self._ordered(active)
        out = []
        for screen in active:
            entry = placed.get(str(screen["n"])) or {}
            out.append({**{k: v for k, v in screen.items() if k != "surface"},
                        "kind": clean_surface(screen.get("surface"))["kind"], "room": entry.get("room"),
                        "neighbors": {side: entry.get(side) for side in SIDES}})
        return out

    def room_of(self, n: int) -> str | None:
        return (self.poses().get(n) or {}).get("room")

    def sensed_rooms(self) -> list[str]:
        now = time.monotonic()
        if now - self._sensed[0] < SENSED_TTL:
            return list(self._sensed[1])
        try:
            from features.cameras.live import all_rows
            rows = all_rows()
        except (ImportError, OSError) as exc:
            log.warning("Stanze delle telecamere non disponibili: %s", exc)
            rows = []
        rooms = sorted({slug(r.get("room")) for r in rows if r.get("main") and ROOM.match(slug(r.get("room")))})
        self._sensed = (now, rooms)
        return list(rooms)

    def audience_for(self, n: int, kind: str) -> str:
        return self.audience_in(self.room_of(n), kind)

    def audience_in(self, room: str | None, kind: str) -> str:
        kind = kind if kind in AUDIENCES else "uncertain"
        if room is None:
            return kind
        sensed = self.sensed_rooms()
        payload = {"global": kind, "rooms": {r: kind for r in sensed}, "sensed": sensed, "strict": strict()}
        engine = _native("surface_audience")
        if engine is not None:
            return json.loads(engine(json.dumps(payload), room))
        if room in sensed or not payload["strict"]:
            return kind
        return "uncertain"


surfaces = Surfaces()
