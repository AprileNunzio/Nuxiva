import hashlib
import json
import logging
import os
import threading
import time
from collections import deque

from config import STATE_DIR

from agenti.firewall import model

JOURNAL = STATE_DIR / "firewall" / "journal.jsonl"
MAX_BYTES = 4 * 1024 * 1024
KEEP = 500
FIELDS = ("action", "kind", "target", "minutes", "reason", "incident", "by", "ok", "detail")
log = logging.getLogger("nuxiva.firewall")


def _digest(previous: str, entry: dict) -> str:
    body = json.dumps(entry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256((previous + body).encode()).hexdigest()


class Journal:

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.recent: deque[dict] = deque(maxlen=KEEP)
        self.head = "0" * 64
        self._load()

    def _load(self) -> None:
        try:
            lines = JOURNAL.read_text(encoding="utf-8").splitlines()[-KEEP:]
        except FileNotFoundError:
            return
        except OSError as exc:
            log.error("Registro della difesa illeggibile: %s", exc)
            return
        for line in lines:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict) and isinstance(entry.get("hash"), str):
                self.recent.append(entry)
                self.head = entry["hash"]

    def record(self, **fields) -> dict:
        entry = {k: fields.get(k) for k in FIELDS if k in fields}
        for key in ("target", "reason", "detail", "by", "incident"):
            if isinstance(entry.get(key), str):
                entry[key] = model.comment(entry[key])[:160] if key != "target" else entry[key][:80]
        entry["at"] = round(time.time(), 3)
        with self.lock:
            entry["prev"] = self.head
            entry["hash"] = _digest(self.head, {k: v for k, v in entry.items() if k != "hash"})
            self.head = entry["hash"]
            self.recent.append(entry)
            try:
                self._append(entry)
            except OSError as exc:
                log.error("Registro della difesa non scritto: %s", exc)
        return entry

    def _append(self, entry: dict) -> None:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        if JOURNAL.exists() and JOURNAL.stat().st_size > MAX_BYTES:
            JOURNAL.replace(JOURNAL.with_suffix(".1.jsonl"))
        fd = os.open(JOURNAL, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def verify(self) -> bool:
        with self.lock:
            entries = list(self.recent)
        for before, after in zip(entries, entries[1:]):
            if after.get("prev") != before.get("hash"):
                return False
        return all(e.get("hash") == _digest(e.get("prev", ""), {k: v for k, v in e.items() if k != "hash"}) for e in entries)

    def tail(self, limit: int = 100) -> list[dict]:
        with self.lock:
            return list(self.recent)[-max(1, min(limit, KEEP)):]


journal = Journal()
