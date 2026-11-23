from __future__ import annotations

import os
import secrets
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from config import STATE_DIR

from . import parse

LOG_DIR = STATE_DIR / "apt_phase"
KEEP_LOGS = 10
PUBLIC_LINES = 14
STEPS = ("update", "upgrade")
STATUSES = frozenset({"idle", "running", "done", "failed", "skipped"})
STEP_WEIGHT = {"update": (0, 30), "upgrade": (30, 70)}


class AptPhase:
    def __init__(self, log_dir: Path = LOG_DIR) -> None:
        self.log_dir = log_dir
        self.lines: Deque[Dict[str, Any]] = deque(maxlen=PUBLIC_LINES)
        self.data: Dict[str, Any] = self._empty("idle")
        self._log: Optional[Any] = None

    @staticmethod
    def _empty(status: str) -> Dict[str, Any]:
        return {"id": "", "status": status, "step": None, "steps": {s: "pending" for s in STEPS}, "summary": None,
                "fetched": 0, "unpacked": 0, "configured": 0, "warnings": 0, "errors": 0, "package": None,
                "percent": 0, "started": None, "finished": None, "error": None}

    def begin(self) -> str:
        self.close()
        self.lines.clear()
        self.data = self._empty("running")
        self.data["id"] = secrets.token_hex(6)
        self.data["started"] = time.time()
        self._open_log()
        return self.data["id"]

    def skip(self, reason: str) -> None:
        self.close()
        self.lines.clear()
        self.data = self._empty("skipped")
        self.data.update(id=secrets.token_hex(6), error=reason[:48], started=time.time(), finished=time.time())

    def _open_log(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.log_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{self.data['id']}.log"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        self._log = os.fdopen(fd, "w", encoding="utf-8")
        self._prune()

    def _prune(self) -> None:
        logs = sorted(p for p in self.log_dir.glob("*.log") if p.is_file() and not p.is_symlink())
        for old in logs[:-KEEP_LOGS]:
            old.unlink(missing_ok=True)

    def _write(self, text: str) -> None:
        if self._log is not None:
            self._log.write(text + "\n")
            self._log.flush()

    def step(self, step: str, status: str) -> None:
        if step not in STEPS or status not in {"running", "done", "failed"}:
            raise ValueError("invalid apt step")
        self.data["steps"][step] = status
        if status == "running":
            self.data["step"] = step
            self.data["summary"] = self.data["summary"] if step == "upgrade" else None
        self._write(f"### {step} {status}")
        self._recompute()

    def feed(self, raw: str) -> Dict[str, Any]:
        line = parse.classify(raw)
        kind, text = line["kind"], line["text"]
        if not text:
            return line
        self._write(text)
        counters = {"fetch": "fetched", "unpack": "unpacked", "setup": "configured", "warn": "warnings", "error": "errors"}
        if kind in counters:
            self.data[counters[kind]] += 1
        if kind == "summary" and self.data["step"] == "upgrade":
            self.data["summary"] = line["summary"]
        if line.get("package"):
            self.data["package"] = line["package"]
        self.lines.append({"k": kind, "t": text})
        self._recompute()
        return line

    def _recompute(self) -> None:
        step = self.data["step"]
        if step is None:
            return
        base, span = STEP_WEIGHT[step]
        state = self.data["steps"][step]
        if state in ("done", "failed"):
            inner = 100
        elif step == "update":
            inner = min(95, self.data["fetched"] * 8)
        else:
            inner = parse.percent(self.data["summary"], self.data["unpacked"], self.data["configured"])
        self.data["percent"] = min(100, base + span * inner // 100)

    def finish(self, status: str, error: Optional[str] = None) -> None:
        if status not in STATUSES:
            raise ValueError("invalid apt status")
        self.data.update(status=status, finished=time.time(), error=(error or None) and error[:48], package=None)
        if status == "done":
            self.data["percent"] = 100
        self._write(f"### finish {status} {error or ''}".rstrip())
        self.close()

    def close(self) -> None:
        if self._log is not None:
            self._log.close()
            self._log = None

    def tail(self) -> List[str]:
        return [entry["t"] for entry in self.lines]

    def public(self) -> Optional[Dict[str, Any]]:
        if self.data["status"] == "idle":
            return None
        keys = ("id", "status", "step", "steps", "summary", "fetched", "unpacked", "configured", "warnings",
                "errors", "package", "percent", "started", "finished", "error")
        view = {key: self.data[key] for key in keys}
        view["lines"] = list(self.lines)
        return view


phase = AptPhase()
