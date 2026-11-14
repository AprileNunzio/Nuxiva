import json
import logging
import threading
import time
from pathlib import Path

from agenti.autonomy import proactivity_schema as sc

log = logging.getLogger("nuxiva.autonomy.proactivity")
RULES = Path(__file__).with_name("proactivity_rules.json")
_lock = threading.Lock()
_engine = {"obj": None}
_handlers = {"done": False}


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustProactivity", None)


def now_ms() -> int:
    return int(time.time() * 1000)


def rules_text() -> str:
    return RULES.read_text(encoding="utf-8")


def dumps(value) -> str:
    return json.dumps(value, separators=(",", ":"))


def signal(domain: str, key: str, person: str | None = None, subject: str = "", value: int = 0, at: int | None = None) -> str:
    return dumps({"domain": domain, "key": key, "person": person, "subject": subject, "value": int(value), "at": now_ms() if at is None else at})


def build(state_json: str | None = None, settings_json: str = ""):
    cls = native()
    if cls is not None:
        try:
            return cls(settings_json, rules_text(), state_json)
        except ValueError as exc:
            log.error("Proattività nativa non disponibile: %s", exc)
    from agenti.autonomy.proactivity_py import PyProactivity
    return PyProactivity(settings_json, rules_text(), state_json)


def _file() -> Path:
    from config import STATE_DIR
    return STATE_DIR / "proactivity.json"


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
                log.error("Stato della proattività non valido: riparto vuoto")
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


def situation(guests: bool = False) -> str:
    if guests:
        return "guests"
    from agenti.autonomy import initiative
    return initiative.situation()


def audience() -> tuple[list[str], bool]:
    try:
        from agenti.desktop.presence_bridge import bridge
        last = bridge.last
    except (ImportError, AttributeError):
        return [], True
    members = [str(m.get("slug") or m.get("person") or "") for m in last.get("members", []) if isinstance(m, dict)]
    present = [m for m in members if sc.person_ok(m)][:32]
    guests = int(last.get("guests") or 0) > 0 or last.get("kind") in ("guest_only", "mixed", "uncertain")
    return present, guests


def context(voice_free: bool = False) -> str:
    present, guests = audience()
    offset = int(time.localtime().tm_gmtoff // 60) if hasattr(time.localtime(), "tm_gmtoff") else 0
    return dumps({"situation": situation(guests), "voice_free": voice_free, "guests_present": guests, "present": present, "tz_offset_min": max(-840, min(840, offset))})


def visible(decisions: list) -> list:
    return [d for d in decisions if d["mode"] != "diary"]


def feed(domain: str, key: str, person: str | None = None, subject: str = "", value: int = 0, voice_free: bool = False) -> list:
    try:
        out = json.loads(get().ingest(signal(domain, key, person, subject, value), context(voice_free), now_ms()))
    except ValueError as exc:
        log.warning("Segnale di proattività rifiutato: %s", exc)
        return []
    _execute(out)
    shown = visible(out)
    surface(shown)
    return shown


def predict(forecast: dict, voice_free: bool = False) -> list:
    try:
        out = json.loads(get().forecast(dumps(forecast), context(voice_free), now_ms()))
    except ValueError as exc:
        log.warning("Previsione di proattività rifiutata: %s", exc)
        return []
    _execute(out)
    shown = visible(out)
    surface(shown)
    return shown


def tick(voice_free: bool = False) -> list:
    try:
        out = json.loads(get().tick(context(voice_free), now_ms()))
    except ValueError as exc:
        log.warning("Ciclo di proattività rifiutato: %s", exc)
        return []
    _execute(out)
    shown = visible(out)
    surface(shown)
    return shown


def _execute(decisions: list) -> None:
    for d in decisions:
        if d["mode"] == "execute" and d["action"] is not None:
            _submit(d["action"])


def _submit(spec: dict) -> bool:
    from agenti.tasks import queue as taskq
    _ensure_handlers()
    try:
        taskq.get().submit(json.dumps(spec))
    except (ValueError, RuntimeError, OSError) as exc:
        log.error("Azione proattiva non accodata: %s", exc)
        return False
    return True


def _ensure_handlers() -> None:
    if _handlers["done"]:
        return
    from agenti.tasks import queue as taskq
    for kind in sorted({r["action"]["kind"] for r in json.loads(rules_text())["rules"].values()}
                       | {r["action"]["undo"]["kind"] for r in json.loads(rules_text())["rules"].values() if r["action"].get("undo")}):
        taskq.register(kind, _runner(kind))
    _handlers["done"] = True


def _runner(kind: str):
    def run(input_ref: str, scope) -> list:
        from agenti.mcpclient import brain
        outcome = brain.dispatch(f"{kind} {input_ref}", "nuxiva", now_ms())
        if not isinstance(outcome, dict) or not outcome.get("succeeded"):
            raise ValueError("proactive.action_failed")
        return [f"proactive:{kind}"]
    return run


def view() -> dict:
    store = get()
    items = [{"id": p["id"], "summary_key": p["summary_key"], "rule": p["rule"], "redacted": p["redacted"], "undoable": p["undoable"], "actionable": p["action"] is not None}
             for p in json.loads(store.pending())]
    wanted = set(json.loads(store.undoable()))
    undo = [{"id": d["id"], "summary_key": d["summary_key"]} for d in json.loads(store.log()) if d["id"] in wanted]
    return {"items": items[:6], "undo": undo[:6]}


def snapshot() -> dict:
    tick()
    return view()


def surface(decisions: list) -> None:
    if not decisions:
        return
    try:
        from agenti.desktop.desk import desk
        desk.show("proactive", view(), key="proactive", ttl=3600)
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        log.warning("Proposta proattiva non mostrata: %s", exc)


def accept(pid: int) -> bool:
    try:
        spec = json.loads(get().accept(pid, now_ms()))
    except ValueError:
        return False
    save()
    return _submit(spec)


def refuse(pid: int) -> bool:
    try:
        get().refuse(pid, now_ms())
    except ValueError:
        return False
    save()
    return True


def dismiss(pid: int) -> bool:
    try:
        get().dismiss(pid)
    except ValueError:
        return False
    return True


def undo(pid: int) -> bool:
    try:
        spec = json.loads(get().undo(pid, now_ms()))
    except ValueError:
        return False
    save()
    return _submit(spec)


def explain(pid: int) -> dict | None:
    try:
        return json.loads(get().explain(pid))
    except ValueError:
        return None
