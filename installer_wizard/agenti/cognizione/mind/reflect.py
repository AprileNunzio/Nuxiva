import json
import logging
import threading
import time
from pathlib import Path

log = logging.getLogger("nuxiva.mind.reflect")
CATALOG = Path(__file__).with_name("lessons_catalog.json")
STATES = ("candidate", "adopted", "rejected", "expired")
_lock = threading.Lock()
_store = {"obj": None}


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustReflect", None)


def now_ms() -> int:
    return int(time.time() * 1000)


def catalog_text() -> str:
    return CATALOG.read_text(encoding="utf-8")


def reflection(task: str, outcome: str, attempts: int = 1, observed=(), proposed=None, corrections: int = 0, rejections: int = 0,
               duration_ms: int = 0) -> str:
    body = {"schema_version": 1, "task": task, "outcome": outcome,
            "signals": {"duration_ms": duration_ms, "attempts": attempts, "user_corrections": corrections, "user_rejections": rejections},
            "observed": [{"kind": k, "value": v} for k, v in observed], "proposed": None}
    if proposed:
        body["proposed"] = {"type": "data", "candidate": {"kind": proposed[0], "value": proposed[1]}}
    return json.dumps(body, separators=(",", ":"))


class PyReflect:
    def __init__(self, settings_json: str, catalog_json: str, snapshot_json: str | None = None) -> None:
        self._kinds = json.loads(catalog_json)["kinds"]
        self._lessons: dict = {}
        self._blocked: dict = {}
        self._next = 1
        self._code: list = []
        if snapshot_json:
            data = json.loads(snapshot_json)
            self._lessons = {l["id"]: l for l in data.get("lessons", [])}
            self._next = data.get("next_id", 1)

    def _check(self, kind: str, value: str) -> dict:
        spec = self._kinds.get(kind)
        if spec is None:
            raise ValueError("reflect.unknown_kind")
        allowed = spec.get("allowed_values", [])
        if not value or len(value) > spec["max_value_len"] or (allowed and value not in allowed):
            raise ValueError("reflect.bad_value")
        return spec

    def record(self, reflection_json: str, now: int) -> str:
        data = json.loads(reflection_json)
        if data.get("schema_version") != 1:
            raise ValueError("reflect.version")
        for o in data.get("observed", []):
            self._check(o["kind"], o["value"])
        out = {"candidate": None, "adopted": [], "blocked": False, "code_request": None}
        proposed = data.get("proposed")
        if proposed and proposed["type"] == "data":
            kind, value = proposed["candidate"]["kind"], proposed["candidate"]["value"]
            spec = self._check(kind, value)
            if self._blocked.get((kind, value), 0) > now:
                out["blocked"] = True
            else:
                found = next((l for l in self._lessons.values() if l["kind"] == kind and l["value"] == value and l["state"] in ("candidate", "adopted")), None)
                if found:
                    found["evidence"] += 1
                    out["candidate"] = found["id"]
                else:
                    lid, self._next = self._next, self._next + 1
                    self._lessons[lid] = {"id": lid, "kind": kind, "domain": spec["domain"], "value": value, "state": "candidate", "version": 0,
                                          "evidence": 1, "user_confirmed": False, "created_at": now, "confirmed_at": now}
                    out["candidate"] = lid
        elif proposed:
            self._code.append(proposed["request_ref"])
            out["code_request"] = proposed["request_ref"]
        return json.dumps(out)

    def confirm(self, lid: int, now: int) -> None:
        lesson = self._lessons.get(lid)
        if lesson is None:
            raise ValueError("reflect.not_found")
        if lesson["state"] not in ("candidate", "adopted"):
            raise ValueError("reflect.state")
        for other in self._lessons.values():
            if other["kind"] == lesson["kind"] and other["state"] == "adopted" and other["id"] != lid:
                other["state"] = "expired"
        lesson.update(state="adopted", user_confirmed=True, confirmed_at=now, version=max(lesson["version"], 1))

    def reject(self, lid: int, now: int) -> None:
        lesson = self._lessons.get(lid)
        if lesson is None:
            raise ValueError("reflect.not_found")
        if lesson["state"] in ("rejected", "expired"):
            raise ValueError("reflect.state")
        lesson["state"] = "rejected"
        self._blocked[(lesson["kind"], lesson["value"])] = now + 30 * 86_400_000

    def revert(self, kind: str, now: int) -> None:
        lesson = next((l for l in self._lessons.values() if l["kind"] == kind and l["state"] == "adopted"), None)
        if lesson is None:
            raise ValueError("reflect.not_found")
        lesson["state"] = "expired"

    def maintain(self, now: int) -> None:
        return None

    def lessons(self, state: str) -> str:
        if state not in STATES:
            raise ValueError("reflect.invalid")
        return json.dumps([l for l in self._lessons.values() if l["state"] == state])

    def lesson_for(self, kind: str):
        found = next((l for l in self._lessons.values() if l["kind"] == kind and l["state"] == "adopted"), None)
        return json.dumps(found) if found else None

    def take_code_requests(self) -> str:
        out, self._code = self._code, []
        return json.dumps(out)

    def export(self) -> str:
        return json.dumps({"next_id": self._next, "lessons": list(self._lessons.values())})


def build(snapshot_json: str | None = None, settings_json: str = ""):
    cls = native()
    if cls is not None:
        try:
            return cls(settings_json, catalog_text(), snapshot_json)
        except ValueError as exc:
            log.error("Riflessione nativa non disponibile: %s", exc)
    return PyReflect(settings_json, catalog_text(), snapshot_json)


def _file() -> Path:
    from config import STATE_DIR
    return STATE_DIR / "lessons.json"


def get():
    with _lock:
        if _store["obj"] is None:
            snapshot = None
            try:
                snapshot = _file().read_text(encoding="utf-8")
            except OSError:
                pass
            try:
                _store["obj"] = build(snapshot)
            except (ValueError, RuntimeError, json.JSONDecodeError, KeyError):
                log.error("Archivio delle lezioni non valido: riparto vuoto")
                _store["obj"] = build(None)
        return _store["obj"]


def save() -> None:
    from sealed import write_private
    with _lock:
        obj = _store["obj"]
        if obj is not None:
            write_private(_file(), obj.export().encode("utf-8"))


def reset() -> None:
    with _lock:
        _store["obj"] = None


def snapshot() -> dict:
    store = get()
    store.maintain(now_ms())
    items: list = []
    for state in ("adopted", "candidate"):
        items.extend({"id": l["id"], "kind": l["kind"], "value": l["value"], "state": state} for l in json.loads(store.lessons(state)))
    return {"items": items[:20]}


def keep(lesson_id: int) -> bool:
    try:
        get().confirm(lesson_id, now_ms())
    except ValueError:
        return False
    save()
    return True


def forget(lesson_id: int) -> bool:
    try:
        get().reject(lesson_id, now_ms())
    except ValueError:
        return False
    save()
    return True
