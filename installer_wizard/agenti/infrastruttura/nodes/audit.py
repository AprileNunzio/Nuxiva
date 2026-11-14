import json
import logging
import os
import threading
import time

from config import STATE_DIR

from agenti.nodes import zerotrust

log = logging.getLogger("nuxiva.nodes.audit")

AUDIT_FILE = STATE_DIR / "nodes_audit.jsonl"
ANCHOR_FILE = STATE_DIR / "nodes_audit.anchor"
KEEP = 4000
SLACK = 500
GENESIS = "0" * 64


class AuditLog:
    def __init__(self, path=AUDIT_FILE, anchor_path=ANCHOR_FILE) -> None:
        self.path = path
        self.anchor_path = anchor_path
        self.lock = threading.Lock()
        self.anchor = self._read_anchor()
        self.entries = self._load()

    def _read_anchor(self) -> str:
        try:
            value = self.anchor_path.read_text(encoding="ascii").strip()
        except OSError:
            return GENESIS
        return value if len(value) == 64 else GENESIS

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            log.error("Registro di audit illeggibile: %s", exc)
            return []
        for line in lines[-(KEEP + SLACK):]:
            try:
                item = json.loads(line)
            except ValueError:
                log.error("Riga di audit non valida ignorata")
                continue
            if isinstance(item, dict):
                out.append(item)
        return out

    @staticmethod
    def _write(path, text: str, mode: str) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | (os.O_APPEND if mode == "a" else os.O_TRUNC), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)

    def _compact(self) -> None:
        dropped, self.entries = self.entries[:-KEEP], self.entries[-KEEP:]
        self.anchor = dropped[-1]["hash"]
        tmp = self.path.with_suffix(".tmp")
        self._write(tmp, "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in self.entries), "w")
        os.replace(tmp, self.path)
        self._write(self.anchor_path, self.anchor, "w")

    def record(self, actor: str, node: str, action: str, detail: str = "") -> dict:
        with self.lock:
            last = self.entries[-1] if self.entries else None
            prev = last["hash"] if last else self.anchor
            seq = last["seq"] + 1 if last else 1
            entry = zerotrust.audit_seal(prev, seq, int(time.time()), str(actor), str(node), str(action), str(detail))
            self.entries.append(entry)
            self._write(self.path, json.dumps(entry, ensure_ascii=False) + "\n", "a")
            if len(self.entries) > KEEP + SLACK:
                self._compact()
            return entry

    def tail(self, limit: int = 100) -> list[dict]:
        with self.lock:
            return list(reversed(self.entries[-max(1, min(int(limit), 500)):]))

    def verify(self) -> dict:
        with self.lock:
            snapshot = list(self.entries)
            anchor = self.anchor
        broken = zerotrust.audit_verify(anchor, snapshot)
        return {"ok": broken < 0, "broken_at": None if broken < 0 else broken, "entries": len(snapshot)}


audit = AuditLog()
