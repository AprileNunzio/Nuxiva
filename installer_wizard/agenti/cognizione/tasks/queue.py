import heapq
import itertools
import json
import logging
import re
import threading

log = logging.getLogger("nuxiva.tasks.queue")

ID_RE = re.compile(r"^[a-z0-9._:-]{1,128}$")
CLASSES = ("voice", "interactive", "background", "maintenance")
CONCURRENCY = {"voice": 2, "interactive": 4, "background": 4, "maintenance": 1}
SPEC_KEYS = {"schema_version", "id", "parent", "kind", "class", "priority", "deps", "scope", "budget", "risk_max", "input_ref", "idem_key"}
TERMINAL = ("done", "failed", "cancelled", "expired")
_handlers: dict = {}
_lock = threading.Lock()
_queue = {"obj": None}


def register(kind: str, fn) -> None:
    _handlers[kind] = fn


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustTaskQueue", None)


def spec(task_id: str, kind: str, cls: str = "background", priority: int = 5, input_ref: str = "", wall_ms: int = 600_000,
         risk_max: str = "low", deps=(), parent=None, idem_key=None, scope=()) -> str:
    return json.dumps({
        "schema_version": 1, "id": task_id, "parent": parent, "kind": kind, "class": cls, "priority": priority,
        "deps": list(deps), "scope": list(scope), "budget": {"wall_ms": wall_ms, "tokens": 0, "tool_calls": 0, "cpu_ms": 0},
        "risk_max": risk_max, "input_ref": input_ref, "idem_key": idem_key,
    }, separators=(",", ":"))


def dispatch(spec_json: str) -> str:
    try:
        task = json.loads(spec_json)
        fn = _handlers.get(task["kind"])
        if fn is None:
            return json.dumps({"error": {"code": "task.no_handler", "transient": False}})
        evidence = fn(task["input_ref"], task.get("scope", []))
        return json.dumps({"evidence": [str(x)[:128] for x in (evidence or [])][:64]})
    except TransientError as exc:
        return json.dumps({"error": {"code": str(exc)[:96] or "task.transient", "transient": True}})
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        log.error("Compito fallito: %s", type(exc).__name__)
        return json.dumps({"error": {"code": "task.failed", "transient": False}})


class TransientError(Exception):
    pass


class PyQueue:
    def __init__(self, handler, settings_json: str = "", journal_path: str | None = None) -> None:
        self._handler = handler
        self._cv = threading.Condition()
        self._heap: list = []
        self._tasks: dict[str, dict] = {}
        self._idem: dict[str, str] = {}
        self._running = {c: 0 for c in CLASSES}
        self._events: list = []
        self._seq = itertools.count()
        self._stop = False
        self._pool = [threading.Thread(target=self._loop, daemon=True, name=f"taskq-{c}-{i}") for c in CLASSES for i in range(CONCURRENCY[c])]
        for t in self._pool:
            t.start()

    def _emit(self, task: dict, evidence=()):
        self._events.append({"id": task["id"], "state": task["state"], "class": task["class"], "attempt": task["attempt"],
                             "progress": 100 if task["state"] == "done" else 0, "evidence": list(evidence), "error": task.get("error")})

    def submit(self, spec_json: str) -> str:
        data = json.loads(spec_json)
        if set(data) - SPEC_KEYS or data.get("schema_version") != 1 or data.get("class") not in CLASSES or not ID_RE.fullmatch(str(data.get("id"))):
            raise ValueError("taskq.invalid")
        with self._cv:
            key = data.get("idem_key")
            if key and key in self._idem and self._tasks[self._idem[key]]["state"] not in ("failed", "cancelled", "expired"):
                return f"duplicate:{self._idem[key]}"
            if data["id"] in self._tasks:
                raise ValueError("taskq.invalid")
            task = {"id": data["id"], "class": data["class"], "spec": data, "state": "queued", "attempt": 0}
            self._tasks[data["id"]] = task
            if key:
                self._idem[key] = data["id"]
            heapq.heappush(self._heap, (-data["priority"], next(self._seq), data["id"]))
            self._emit(task)
            self._cv.notify_all()
        return "accepted"

    def _pick(self, cls: str):
        skipped = []
        found = None
        while self._heap:
            item = heapq.heappop(self._heap)
            task = self._tasks[item[2]]
            if task["state"] != "queued":
                continue
            if task["class"] == cls:
                found = task
                break
            skipped.append(item)
        for item in skipped:
            heapq.heappush(self._heap, item)
        return found

    def _loop(self) -> None:
        cls = threading.current_thread().name.split("-")[1]
        while True:
            with self._cv:
                task = None
                while not self._stop:
                    if self._running[cls] < CONCURRENCY[cls]:
                        task = self._pick(cls)
                    if task:
                        break
                    self._cv.wait(0.2)
                if self._stop:
                    return
                task["state"], task["attempt"] = "running", task["attempt"] + 1
                self._running[cls] += 1
                self._emit(task)
            try:
                reply = json.loads(self._handler(json.dumps(task["spec"])))
            except (ValueError, TypeError):
                reply = {"error": {"code": "taskq.bridge.reply", "transient": False}}
            with self._cv:
                self._running[cls] -= 1
                if task["state"] == "running":
                    task["state"] = "failed" if "error" in reply else "done"
                    task["error"] = reply.get("error")
                    self._emit(task, reply.get("evidence", ()))
                self._cv.notify_all()

    def cancel(self, task_id: str) -> None:
        with self._cv:
            task = self._tasks.get(task_id)
            if task is None:
                raise ValueError("taskq.not_found")
            if task["state"] in TERMINAL:
                raise ValueError("taskq.terminal")
            task["state"] = "cancelled"
            self._emit(task)

    def status(self, task_id: str):
        with self._cv:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return json.dumps({"id": task["id"], "state": task["state"], "class": task["class"], "attempt": task["attempt"],
                               "progress": 100 if task["state"] == "done" else 0, "evidence": [], "error": task.get("error")})

    def events(self, limit: int) -> str:
        with self._cv:
            out, self._events = self._events[:limit], self._events[limit:]
        return json.dumps(out)

    def stats(self) -> str:
        with self._cv:
            out = {c: {"queued": 0, "running": self._running[c]} for c in CLASSES}
            for task in self._tasks.values():
                if task["state"] == "queued":
                    out[task["class"]]["queued"] += 1
        return json.dumps({**out, "journal_errors": 0, "dropped_events": 0})

    def shutdown(self) -> None:
        with self._cv:
            self._stop = True
            self._cv.notify_all()


def build(handler=None, settings_json: str = "", journal_path: str = ""):
    handler = handler or dispatch
    cls = native()
    if cls is not None:
        try:
            return cls(settings_json, handler, journal_path or None)
        except (ValueError, RuntimeError) as exc:
            log.error("Coda nativa non disponibile: %s", exc)
    return PyQueue(handler, settings_json, journal_path)


_kinds: dict = {}
_live: dict = {}


def enqueue(task_id: str, kind: str, **fields) -> str:
    out = get().submit(spec(task_id, kind, **fields))
    _kinds[task_id] = kind
    return out


def cancel(task_id: str) -> bool:
    try:
        get().cancel(task_id)
    except ValueError:
        return False
    return True


def snapshot(limit: int = 12) -> dict:
    q = get()
    for event in json.loads(q.events(4096)):
        _live[event["id"]] = event
    rows = [{"id": e["id"], "kind": _kinds.get(e["id"], "other"), "state": e["state"], "progress": e["progress"]} for e in _live.values()]
    for key in [k for k, e in _live.items() if e["state"] in TERMINAL][:-3]:
        _live.pop(key, None)
        _kinds.pop(key, None)
    active = [r for r in rows if r["state"] not in TERMINAL]
    return {"items": (active + [r for r in rows if r["state"] in TERMINAL])[:limit], "active": len(active), "stats": json.loads(q.stats())}


def get():
    with _lock:
        if _queue["obj"] is None:
            from config import STATE_DIR
            _queue["obj"] = build(journal_path=str(STATE_DIR / "taskq.journal"))
        return _queue["obj"]


def reset() -> None:
    with _lock:
        obj, _queue["obj"] = _queue["obj"], None
    if obj is not None:
        try:
            obj.shutdown()
        except (RuntimeError, ValueError):
            pass
