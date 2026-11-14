import json
import logging
import threading
import time
from pathlib import Path

log = logging.getLogger("nuxiva.autonomy.initiative")
CATALOG = Path(__file__).with_name("initiatives.json")
SITUATIONS = ("idle", "conversation", "sleeping", "guests", "meeting")
HOUR_MS = 3_600_000
_lock = threading.Lock()
_engine = {"obj": None}


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustInitiative", None)


def now_ms() -> int:
    return int(time.time() * 1000)


def catalog_text() -> str:
    return CATALOG.read_text(encoding="utf-8")


def event(source: str, topic: str, subject: str, at: int | None = None) -> str:
    return json.dumps({"source": source, "topic": topic, "subject": subject, "at": now_ms() if at is None else at}, separators=(",", ":"))


class PyInitiative:
    def __init__(self, settings_json: str, catalog_json: str, state_json: str | None = None) -> None:
        self._observers = json.loads(catalog_json)["observers"]
        self._pending: list = []
        self._seen: dict = {}
        self._surfaced: list = []
        self._next = 1
        self._refused: dict = {}
        self._stats = {"surfaced": 0, "accepted": 0, "refused": 0, "silent": 0, "capped": 0, "expired": 0}

    def observe(self, event_json: str, situation: str, voice_free: bool, now: int) -> str:
        ev = json.loads(event_json)
        if situation not in SITUATIONS:
            raise ValueError("initiative.invalid")
        out = []
        for oid, obs in self._observers.items():
            if obs["source"] != ev["source"] or obs["topic"] != ev["topic"] or not ev["subject"].startswith(obs.get("subject_prefix", "")):
                continue
            key = f"{oid}|{ev['subject']}"
            if now - self._seen.get(key, -10**15) <= 600_000:
                continue
            self._seen[key] = now
            self._surfaced = [t for t in self._surfaced if now - t < HOUR_MS]
            quiet = situation in ("conversation", "sleeping") or (obs["value"] * obs["confidence"]) // 1000 <= {"idle": 100, "guests": 600, "meeting": 800}.get(situation, 1000)
            capped = not quiet and len(self._surfaced) >= 6
            diary = quiet or capped or obs["level"] == "silent" or self._refused.get(oid, 0) > now
            mode = "diary" if diary else ("speak" if voice_free and situation == "idle" else "widget")
            action = {"schema_version": 1, "id": f"init.{oid}.{self._next}", "parent": None, "kind": obs["action"]["kind"], "class": obs["action"]["class"],
                      "priority": obs["action"]["priority"], "deps": [], "scope": [], "budget": obs["action"]["budget"], "risk_max": obs["action"]["risk_max"],
                      "input_ref": obs["action"]["input_template"].replace("{subject}", ev["subject"]), "idem_key": None}
            p = {"id": self._next, "observer": oid, "summary_key": obs["summary_key"], "subject": ev["subject"], "action": action, "mode": mode,
                 "expires_at": now + 3_600_000}
            self._next += 1
            if capped:
                self._stats["capped"] += 1
            if mode == "diary":
                self._stats["silent"] += 1
            else:
                self._surfaced.append(now)
                self._stats["surfaced"] += 1
                self._pending.append(p)
            out.append(p)
        return json.dumps(out)

    def tick(self, situation: str, voice_free: bool, now: int) -> str:
        self._pending = [p for p in self._pending if p["expires_at"] > now]
        return "[]"

    def accept(self, pid: int, now: int) -> str:
        for p in self._pending:
            if p["id"] == pid:
                self._pending.remove(p)
                self._stats["accepted"] += 1
                return json.dumps(p["action"])
        raise ValueError("initiative.not_found")

    def refuse(self, pid: int, now: int) -> None:
        for p in self._pending:
            if p["id"] == pid:
                self._pending.remove(p)
                self._refused[p["observer"]] = now + 86_400_000
                self._stats["refused"] += 1
                return
        raise ValueError("initiative.not_found")

    def approve_always(self, observer: str) -> None:
        obs = self._observers.get(observer)
        if obs is None:
            raise ValueError("initiative.not_found")
        if obs["action"]["risk_max"] not in ("none", "low"):
            raise ValueError("initiative.consent")

    def revoke(self, observer: str) -> None:
        return None

    def pending(self) -> str:
        return json.dumps(self._pending)

    def diary(self) -> str:
        return "[]"

    def stats(self) -> str:
        decided = self._stats["accepted"] + self._stats["refused"]
        return json.dumps({**self._stats, "acceptance_permille": self._stats["accepted"] * 1000 // decided if decided else None})

    def export_state(self) -> str:
        return json.dumps({"approved": [], "refusals": {}})


def build(state_json: str | None = None, settings_json: str = ""):
    cls = native()
    if cls is not None:
        try:
            return cls(settings_json, catalog_text(), state_json)
        except ValueError as exc:
            log.error("Iniziativa nativa non disponibile: %s", exc)
    return PyInitiative(settings_json, catalog_text(), state_json)


def _file() -> Path:
    from config import STATE_DIR
    return STATE_DIR / "initiative.json"


def get():
    with _lock:
        if _engine["obj"] is None:
            state = None
            try:
                state = _file().read_text(encoding="utf-8")
            except OSError:
                pass
            try:
                _engine["obj"] = build(state)
            except (ValueError, RuntimeError):
                log.error("Stato dell'iniziativa non valido: riparto vuoto")
                _engine["obj"] = build(None)
        return _engine["obj"]


def reset() -> None:
    with _lock:
        _engine["obj"] = None


def save() -> None:
    from sealed import write_private
    with _lock:
        obj = _engine["obj"]
        if obj is not None:
            write_private(_file(), obj.export_state().encode("utf-8"))


def situation() -> str:
    hour = time.localtime().tm_hour
    if hour >= 23 or hour < 7:
        return "sleeping"
    try:
        from agenti.agent.agent import agent
        if getattr(agent, "busy", False):
            return "conversation"
    except ImportError:
        pass
    return "idle"


def feed(source: str, topic: str, subject: str, voice_free: bool = False, state: str | None = None) -> list:
    out = json.loads(get().observe(event(source, topic, subject), state or situation(), voice_free, now_ms()))
    return [p for p in out if p["mode"] != "diary"]


def tick(voice_free: bool = False) -> list:
    return json.loads(get().tick(situation(), voice_free, now_ms()))


def snapshot() -> dict:
    store = get()
    store.tick(situation(), False, now_ms())
    items = [{"id": p["id"], "summary_key": p["summary_key"], "observer": p["observer"]} for p in json.loads(store.pending())]
    return {"items": items[:6]}


def accept(pid: int) -> bool:
    from agenti.tasks import queue as taskq
    _ensure_handlers()
    try:
        spec = json.loads(get().accept(pid, now_ms()))
        taskq.get().submit(json.dumps(spec))
    except ValueError:
        return False
    return True


def refuse(pid: int) -> bool:
    try:
        get().refuse(pid, now_ms())
    except ValueError:
        return False
    save()
    return True


_mtimes: dict = {}
_handlers = {"done": False}


def _ensure_handlers() -> None:
    if _handlers["done"]:
        return
    import asyncio
    from agenti.devstudio import runner, workspace
    from agenti.tasks import queue as taskq

    def dev_check(input_ref: str, scope) -> list:
        folder = workspace.project_dir(input_ref.removeprefix("project:"))
        code, _text = asyncio.run(runner.run("python_tests", folder))
        if code != 0:
            raise ValueError("check.failed")
        return [f"exit:{code}"]

    taskq.register("dev_check", dev_check)
    _handlers["done"] = True


def poll_projects() -> list:
    try:
        from agenti.devstudio import workspace
        folders = sorted(p for p in workspace.ROOT.iterdir() if p.is_dir()) if workspace.ROOT.is_dir() else []
    except (ImportError, OSError):
        return []
    out: list = []
    for folder in folders:
        try:
            stamp = max((f.stat().st_mtime_ns for f in folder.rglob("*") if f.is_file()), default=0)
        except OSError:
            continue
        before = _mtimes.get(folder.name)
        _mtimes[folder.name] = stamp
        if before is not None and stamp > before:
            out.extend(feed("fs", "modified", f"project:{folder.name}"))
    return out
