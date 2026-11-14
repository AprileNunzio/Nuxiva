import secrets
import threading
import time

from autonomy.vault import Vault

MAX_TURNS = 400
MAX_TEXT = 600
SYNC_BATCH = 40


class LocalMemory:
    def __init__(self, vault: Vault, clock=time.time) -> None:
        self.vault, self.clock = vault, clock
        self.lock = threading.Lock()
        self.turns: list[dict] = [t for t in self.vault.read().get("turns", []) if self._valid(t)][-MAX_TURNS:]

    @staticmethod
    def _valid(turn) -> bool:
        return (isinstance(turn, dict) and isinstance(turn.get("id"), str) and isinstance(turn.get("text"), str)
                and isinstance(turn.get("reply"), str))

    def record(self, text: str, reply: str, synced: bool = False) -> str:
        entry = {"id": secrets.token_hex(8), "at": int(self.clock()), "text": text[:MAX_TEXT], "reply": reply[:MAX_TEXT],
                 "synced": synced}
        with self.lock:
            self.turns = [*self.turns, entry][-MAX_TURNS:]
            self.vault.write({"turns": self.turns})
        return entry["id"]

    def recent(self, count: int) -> list[dict]:
        with self.lock:
            return list(self.turns[-max(0, count):])

    def pending(self) -> list[dict]:
        with self.lock:
            return [t for t in self.turns if not t.get("synced")][:SYNC_BATCH]

    def mark_synced(self, ids: list[str]) -> None:
        wanted = set(ids)
        with self.lock:
            for turn in self.turns:
                if turn["id"] in wanted:
                    turn["synced"] = True
            self.vault.write({"turns": self.turns})

    def forget(self) -> None:
        with self.lock:
            self.turns = []
            self.vault.write({"turns": []})
