import json
import logging
import os
import time

from config import STATE_DIR
from features.sentinel import record

log = logging.getLogger("nuxiva.sentinel.recalibrate")

STATE_FILE = STATE_DIR / "sentinel_recalibrate.json"
VOICE_THRESH_BOUNDS = (0.55, 0.85)
VOICE_MARGIN_BOUNDS = (0.04, 0.15)
GAIT_THRESH_BOUNDS = (0.50, 0.80)

DEFAULT_PARAMETERS = {
    "voice_match_threshold": 0.62,
    "voice_margin": 0.06,
    "gait_threshold": 0.60,
}


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {
        "last_run": 0.0,
        "parameters": dict(DEFAULT_PARAMETERS),
        "history": [],
    }


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, STATE_FILE)
    except OSError as exc:
        log.warning("Impossibile salvare stato di ricalibrazione: %s", exc)


def collect_metrics() -> dict:
    ok_count = 0
    wrong_count = 0
    try:
        from features.ear.journal import journal
        if journal.ready:
            entries = journal.entries(limit=200)
            for e in entries:
                v = e.get("verdict")
                if v == "ok":
                    ok_count += 1
                elif v == "wrong":
                    wrong_count += 1
    except Exception:
        pass

    total = ok_count + wrong_count
    precision = round(ok_count / total, 3) if total > 0 else 1.0

    state = _load_state()
    params = state.get("parameters", dict(DEFAULT_PARAMETERS))

    return {
        "ok_count": ok_count,
        "wrong_count": wrong_count,
        "total_feedback": total,
        "precision": precision,
        "parameters": params,
        "last_run": state.get("last_run", 0.0),
    }


def run_cycle() -> dict:
    metrics = collect_metrics()
    precision = metrics["precision"]
    ok = metrics["ok_count"]
    wrong = metrics["wrong_count"]
    total = metrics["total_feedback"]

    state = _load_state()
    params = dict(state.get("parameters", DEFAULT_PARAMETERS))

    v_match = params.get("voice_match_threshold", 0.62)
    v_margin = params.get("voice_margin", 0.06)
    g_thresh = params.get("gait_threshold", 0.60)

    if total >= 3:
        if precision < 0.75:
            v_match = min(VOICE_THRESH_BOUNDS[1], round(v_match + 0.02, 2))
            v_margin = min(VOICE_MARGIN_BOUNDS[1], round(v_margin + 0.01, 2))
            g_thresh = min(GAIT_THRESH_BOUNDS[1], round(g_thresh + 0.02, 2))
        elif precision >= 0.95 and ok >= 10:
            v_match = max(VOICE_THRESH_BOUNDS[0], round(v_match - 0.01, 2))
            g_thresh = max(GAIT_THRESH_BOUNDS[0], round(g_thresh - 0.01, 2))

    updated_params = {
        "voice_match_threshold": v_match,
        "voice_margin": v_margin,
        "gait_threshold": g_thresh,
    }

    agency_tasks = []
    if precision < 0.80 and wrong >= 2:
        agency_tasks.append({
            "title": "Audit sensori e acustica",
            "detail": f"Precisione scesa al {int(precision * 100)}%: verificare calibrazione microfoni e riverbero",
            "urgency": "medium",
        })

    now = time.time()
    state["last_run"] = now
    state["parameters"] = updated_params
    history = state.get("history", [])
    history.append({
        "timestamp": now,
        "precision": precision,
        "parameters": updated_params,
        "agency_tasks_count": len(agency_tasks),
    })
    state["history"] = history[-30:]
    _save_state(state)

    record.record("self.learned", record.NUXIVA, "sentinel.self.recalibrate",
                  {"precision": str(int(precision * 100)), "tasks": str(len(agency_tasks))},
                  "household", "recalibrate")

    return {
        "timestamp": now,
        "precision": precision,
        "ok_count": ok,
        "wrong_count": wrong,
        "parameters": updated_params,
        "agency_tasks": agency_tasks,
    }
