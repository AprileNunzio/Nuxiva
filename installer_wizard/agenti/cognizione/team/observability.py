import json
import logging

from agenti.team.board import board
from agenti.team.scanner import scanner
from agenti.team.swarm import swarm, mode

log = logging.getLogger("nuxiva.team.observability")
DRIFT_RATIO_WARN = 0.02


def _hot() -> dict:
    try:
        from agenti.people import hot
        ctx = hot._state.get("ctx")
        if ctx is None:
            return {"loaded": False, "persons": 0, "present": 0, "version": 0, "approx_bytes": 0}
        raw = json.loads(ctx.stats())
        return {"loaded": True, **{k: int(raw[k]) for k in ("persons", "present", "version", "approx_bytes")}}
    except (ImportError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        log.warning("statistiche della memoria calda non disponibili: %s", type(exc).__name__)
        return {"loaded": False, "persons": 0, "present": 0, "version": 0, "approx_bytes": 0}


def _squad() -> dict:
    agents = scanner.agents or scanner.scan()
    return {
        "agents": len(agents),
        "workers": sum(1 for a in agents.values() if a.worker),
        "tools": sum(len(a.tools) for a in agents.values()),
        "busy": len(board.current()),
    }


def _engine() -> dict:
    stats = {k: int(v) for k, v in swarm.stats.items()}
    compared = stats.get("compared", 0)
    drift = stats.get("mismatched", 0) / compared if compared else 0.0
    return {"mode": mode(), "available": swarm.available, **stats, "drift": round(drift, 4)}


def _alerts(engine: dict, hot: dict) -> list[str]:
    alerts = []
    if engine["available"] is False:
        alerts.append("engine_unavailable")
    if engine["drift"] > DRIFT_RATIO_WARN:
        alerts.append("decision_drift")
    if engine["errors"]:
        alerts.append("engine_errors")
    if not hot["loaded"]:
        alerts.append("memory_cold")
    return alerts


def snapshot() -> dict:
    engine, hot = _engine(), _hot()
    return {"squad": _squad(), "engine": engine, "memory": hot, "alerts": _alerts(engine, hot)}
