import hashlib
import itertools
import json
import logging
import os
import threading
import time

from agenti.team import routing
from agenti.team.board import board

log = logging.getLogger("nuxiva.team.swarm")

FLAG = "NUXIVA_SWARM_ENGINE"
MODES = ("python", "shadow", "rust")
DEFAULT_MODE = "shadow"
CODE_NO_HANDLER = "swarm.bridge.no_handler"

_counter = itertools.count(1)


def mode() -> str:
    raw = os.environ.get(FLAG, DEFAULT_MODE).strip().lower()
    return raw if raw in MODES else DEFAULT_MODE


def _factory():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustSwarm", None)


def manifest_of(agent) -> dict:
    raw = {"id": agent.id, "name": agent.name, "capabilities": list(agent.capabilities)}
    worker = getattr(agent, "worker", None)
    if worker:
        raw["worker"] = dict(worker)
    return raw


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


class Swarm:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._factory = _factory()
        self._key = ""
        self._engine = None
        self._failed_key = ""
        self._learned_key: object = None
        self._handlers: dict = {}
        self.stats = {"compared": 0, "matched": 0, "mismatched": 0, "errors": 0}

    @property
    def available(self) -> bool:
        return self._factory is not None

    def register_handler(self, agent_id: str, handler) -> None:
        self._handlers[agent_id] = handler

    def _bridge(self, payload: str) -> str:
        try:
            request = json.loads(payload)
            handler = self._handlers.get(request.get("agent"))
            if handler is None:
                return _dump({"error": {"kind": "unavailable", "code": CODE_NO_HANDLER}})
            result = handler(str(request.get("intent", "")), str(request.get("goal", "")), request.get("inputs") or {})
            return _dump({"output": result.get("output"), "evidence": result.get("evidence", [])})
        except (ValueError, TypeError, KeyError, AttributeError, OSError, RuntimeError) as exc:
            log.warning("ponte dello sciame fallito: %s", type(exc).__name__)
            return _dump({"error": {"kind": "internal", "code": "swarm.bridge.failed"}})

    def _engine_for(self, agents: dict):
        if self._factory is None:
            return None
        cards = [routing.card(a) for a in agents.values()]
        manifests = [manifest_of(a) for a in agents.values()]
        key = hashlib.sha256((_dump(cards) + _dump(manifests)).encode()).hexdigest()
        with self._lock:
            if key == self._key and self._engine is not None:
                return self._engine
            if key == self._failed_key:
                return None
            try:
                self._engine = self._factory(_dump(manifests), _dump(cards), self._bridge)
            except (ValueError, RuntimeError) as exc:
                self._engine, self._failed_key = None, key
                log.warning("sciame nativo non disponibile: %s", exc)
                return None
            self._key, self._learned_key = key, None
            return self._engine

    def _sync_learned(self, engine, learned: dict, version: object) -> None:
        stamp = (version, len(learned)) if version is not None else object()
        with self._lock:
            if stamp != self._learned_key:
                engine.set_learned(_dump(learned))
                self._learned_key = stamp

    @staticmethod
    def _meta(risk_max: int = 2, graph_ref: str = "") -> str:
        n = next(_counter)
        meta = {"id": f"r{n}", "input": f"in.{n}", "risk_max": risk_max}
        if graph_ref:
            meta["graph_ref"] = graph_ref
        return _dump(meta)

    def admit(self, agents: dict, text: str, learned: dict, version: object = None, graph_ref: str = "") -> dict | None:
        engine = self._engine_for(agents)
        if engine is None:
            return None
        try:
            self._sync_learned(engine, learned, version)
            return json.loads(engine.admit(text, self._meta(graph_ref=graph_ref), int(time.time() * 1000)))
        except (ValueError, RuntimeError) as exc:
            self.stats["errors"] += 1
            log.warning("ammissione dello sciame fallita: %s", exc)
            return None

    def shadow(self, agents: dict, text: str, routed: dict, learned: dict, version: object = None) -> bool | None:
        if mode() == "python":
            return None
        reply = self.admit(agents, text, learned, version)
        if reply is None:
            return None
        decision = reply["decision"]
        same = (
            decision["conversational"] == routed["conversational"]
            and decision["primary"] == routed["primary"]
            and decision["secondaries"] == routed["secondaries"]
            and decision["level"] == routed["level"]
        )
        self.stats["compared"] += 1
        self.stats["matched" if same else "mismatched"] += 1
        if not same:
            log.warning(
                "sciame e CEO divergono: sciame %s/%s, CEO %s/%s",
                decision["primary"], decision["level"], routed["primary"], routed["level"],
            )
        return same

    def execute(self, agents: dict, reply: dict, now_ms: int | None = None) -> dict | None:
        engine = self._engine_for(agents)
        if engine is None or reply.get("kind") != "task" or reply.get("plan") is None:
            return None
        try:
            report = json.loads(engine.execute(_dump(reply["task"]), _dump(reply["plan"]), int(now_ms if now_ms is not None else time.time() * 1000)))
        except (ValueError, RuntimeError) as exc:
            self.stats["errors"] += 1
            log.warning("esecuzione dello sciame fallita: %s", exc)
            return None
        for step in report["steps"]:
            board.post("swarm", "tutti", f"passo {step['step']}: {step['outcome']}", "esito")
        return report

    def cancel(self) -> None:
        engine = self._engine
        if engine is not None:
            engine.cancel()


swarm = Swarm()
