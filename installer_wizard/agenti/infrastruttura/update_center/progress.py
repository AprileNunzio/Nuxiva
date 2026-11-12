from __future__ import annotations

import json
import logging
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional

from config import STATE_DIR

from agenti.update_center import native

log = logging.getLogger(__name__)

PROGRESS_FILE = STATE_DIR / "update_progress.json"
MAX_LINES = 160
MAX_ARG = 96
LEVELS = {"info", "ok", "warn", "error"}
_CODE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
_ARG_KEY = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
_UNSAFE = re.compile(r"[^\w .:/@+()\-]")
PUBLIC_RUN_KEYS = ("from", "to", "reason", "started_at")


def _arg(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    return _UNSAFE.sub("", str(value))[:MAX_ARG]


class UpdateProgress:
    def __init__(self, path: Path = PROGRESS_FILE) -> None:
        self.path = path
        self.state: Dict[str, Any] = {"run": None, "console": []}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            log.warning("update progress unreadable: %s", exc)
            return
        if isinstance(data, dict) and isinstance(data.get("console"), list):
            self.state = {"run": data.get("run") if isinstance(data.get("run"), dict) else None,
                          "console": data["console"][-MAX_LINES:]}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log.warning("update progress not persisted: %s", exc)

    def log(self, code: str, level: str = "info", stage: Optional[str] = None, **args: Any) -> None:
        if not _CODE.match(code):
            raise ValueError("invalid log code")
        entry = {"t": round(time.time(), 3), "level": level if level in LEVELS else "info", "code": code,
                 "stage": stage, "args": {k: _arg(v) for k, v in args.items() if _ARG_KEY.match(k)}}
        console = self.state["console"]
        console.append(entry)
        del console[:-MAX_LINES]
        self._save()

    def begin(self, from_rev: str, to_rev: str, reason: str) -> None:
        self.state["run"] = {"id": secrets.token_hex(6), "from": str(from_rev)[:64], "to": str(to_rev)[:64],
                             "reason": str(reason)[:48], "started_at": time.time(), "pipeline": None,
                             "signature": None, "integrity": None, "impact": None}
        self.log("run_begin", "info", None, source=str(from_rev)[:7], target=str(to_rev)[:7], reason=reason)

    def step(self, stage: str, status: str, level: Optional[str] = None, **args: Any) -> None:
        run = self.state.get("run")
        if run is None:
            return
        try:
            run["pipeline"] = native.pipeline_advance(run.get("pipeline"), stage, status, time.time())
        except ValueError as exc:
            log.warning("update pipeline rejected %s→%s: %s", stage, status, exc)
            self.log("pipeline_rejected", "warn", stage, reason=str(exc))
            return
        tone = level or {"done": "ok", "failed": "error", "skipped": "warn"}.get(status, "info")
        self.log(f"stage_{status}", tone, stage, **args)

    def attach(self, key: str, value: Dict[str, Any]) -> None:
        run = self.state.get("run")
        if run is not None and key in ("signature", "integrity", "impact"):
            run[key] = value
            self._save()

    def run(self) -> Optional[Dict[str, Any]]:
        return self.state.get("run")

    def public(self) -> Optional[Dict[str, Any]]:
        run = self.state.get("run")
        pipeline = (run or {}).get("pipeline")
        if not run or not pipeline:
            return None
        view = {key: run.get(key) for key in PUBLIC_RUN_KEYS}
        view["from"] = str(view["from"] or "")[:7]
        view["to"] = str(view["to"] or "")[:7]
        view["stages"] = [{"id": s["id"], "status": s["status"]} for s in pipeline.get("stages", [])]
        view["percent"] = pipeline.get("percent", 0)
        view["active"] = pipeline.get("active")
        view["outcome"] = pipeline.get("outcome")
        view["console"] = [{k: e.get(k) for k in ("t", "level", "code", "stage")} for e in self.state["console"][-8:]]
        return view

    def view(self, lines: int = MAX_LINES) -> Dict[str, Any]:
        return {"run": self.state.get("run"), "console": self.state["console"][-lines:]}


tracker = UpdateProgress()
