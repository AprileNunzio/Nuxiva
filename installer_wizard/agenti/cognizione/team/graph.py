import json
import logging
import os
import threading
import time
from collections import deque
from pathlib import Path

import native_core

log = logging.getLogger("nuxiva.team.graph")

MAX_LOG = 200
MAX_WHO = 40
MAX_TARGET = 120
MAX_TEXT = 512
MAX_DEPTH = 6
MAX_ITEMS = 200
MAX_REPLY_CHARS = 200_000
EXPLORE_TOOLS = {"neighbors": "graph_neighbors", "impact": "graph_impact", "locate": "graph_locate", "path": "graph_path"}


def _root() -> Path:
    raw = os.environ.get("NUXIVA_GRAPH_ROOT") or os.environ.get("NUXIVA_DIR") or ""
    return Path(raw) if raw else Path(__file__).resolve().parents[4]


def _clip(value, limit: int) -> str:
    return "".join(ch for ch in str(value or "") if ch.isprintable())[:limit]


class GraphBridge:
    def __init__(self, root: Path | None = None, clock=time.time) -> None:
        self._root = root
        self._clock = clock
        self._lock = threading.Lock()
        self._engine = None
        self._failed = False
        self._tools: set[str] = set()
        self._log: deque[dict] = deque(maxlen=MAX_LOG)
        self.calls = 0

    def _ensure(self):
        with self._lock:
            if self._engine is not None or self._failed:
                return self._engine
            cls = native_core.symbol("RustGraph")
            if cls is None:
                self._failed = True
                native_core.python_fallback("team.graph")
                return None
            try:
                engine = cls(str(self._root or _root()))
                self._tools = {t["name"] for t in json.loads(engine.tools())}
            except (ValueError, RuntimeError, KeyError, TypeError) as exc:
                self._failed = True
                log.error("Mappa del progetto non disponibile: %s", exc)
                return None
            self._engine = engine
            return engine

    @property
    def available(self) -> bool:
        return self._ensure() is not None

    def call(self, who: str, tool: str, arguments: dict | None = None) -> dict:
        engine = self._ensure()
        if engine is None:
            return {"ok": False, "error": "graph.unavailable"}
        if tool not in self._tools:
            return {"ok": False, "error": "graph.unknown_tool"}
        args = {k: v for k, v in (arguments or {}).items() if isinstance(k, str)}
        started = self._clock()
        try:
            failed, text = engine.call(tool, json.dumps(args, ensure_ascii=False, separators=(",", ":")))
        except (ValueError, RuntimeError) as exc:
            failed, text = True, str(exc)
        elapsed = int((self._clock() - started) * 1000)
        self._record(who, tool, args, not failed, elapsed)
        if failed:
            return {"ok": False, "error": _clip(text, 80)}
        if len(text) > MAX_REPLY_CHARS:
            return {"ok": False, "error": "graph.reply_too_large"}
        try:
            return {"ok": True, "data": json.loads(text)}
        except ValueError:
            return {"ok": False, "error": "graph.reply_invalid"}

    def _record(self, who: str, tool: str, args: dict, ok: bool, elapsed: int) -> None:
        target = args.get("target") or args.get("query") or args.get("from") or ""
        entry = {"at": int(self._clock() * 1000), "who": _clip(who, MAX_WHO) or "anonimo", "tool": tool,
                 "target": _clip(target, MAX_TARGET), "ok": ok, "ms": elapsed}
        with self._lock:
            self._log.append(entry)
            self.calls += 1

    def consultations(self, limit: int = 50) -> list[dict]:
        with self._lock:
            return list(self._log)[-max(1, min(MAX_LOG, int(limit))):][::-1]

    def overview(self, who: str = "pannello") -> dict:
        reply = self.call(who, "graph_sync")
        if not reply["ok"]:
            return {"available": False, "error": reply["error"]}
        data = reply["data"]
        keys = ("graph_ref", "files", "packages", "symbols", "sections", "edges", "skipped", "added", "changed", "removed", "unchanged")
        return {"available": True, **{k: data.get(k) for k in keys}}

    @staticmethod
    def _item(hit: dict, depth=0, via=None) -> dict:
        return {"name": _clip(hit.get("name"), MAX_TARGET), "kind": _clip(hit.get("kind"), 24), "path": _clip(hit.get("path"), 240),
                "line": int(hit["line"]) if isinstance(hit.get("line"), int) and hit["line"] >= 0 else 0,
                "depth": int(depth) if isinstance(depth, int) and depth >= 0 else 0, "via": _clip(via, 24)}

    def _flatten(self, data) -> dict:
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            rows = [self._item(r["hit"], r.get("depth", 0), r.get("via")) for r in data["items"][:MAX_ITEMS]
                    if isinstance(r, dict) and isinstance(r.get("hit"), dict)]
            return {"items": rows, "truncated": bool(data.get("truncated"))}
        if isinstance(data, list):
            rows = []
            for index, r in enumerate(data[:MAX_ITEMS]):
                if isinstance(r, dict) and isinstance(r.get("hit"), dict):
                    rows.append(self._item(r["hit"], index, r.get("via")))
                elif isinstance(r, dict):
                    rows.append(self._item(r))
            return {"items": rows, "truncated": len(data) > MAX_ITEMS}
        return {"items": [], "truncated": False}

    def explore(self, who: str, mode: str, target: str, depth: int = 2, other: str = "") -> dict:
        tool = EXPLORE_TOOLS.get(mode)
        if tool is None:
            return {"ok": False, "error": "graph.mode"}
        text = _clip(target, MAX_TEXT).strip()
        if not text:
            return {"ok": False, "error": "graph.target"}
        if mode == "locate":
            reply = self.call(who, tool, {"query": text})
        elif mode == "path":
            reply = self.call(who, tool, {"from": text, "to": _clip(other, MAX_TEXT)})
        else:
            reply = self.call(who, tool, {"target": text, "depth": max(1, min(MAX_DEPTH, int(depth)))})
        return {"ok": True, **self._flatten(reply["data"])} if reply["ok"] else reply


graph = GraphBridge()
