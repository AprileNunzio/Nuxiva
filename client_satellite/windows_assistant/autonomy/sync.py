import logging
import threading

from connection.client import ServerError, Unauthorized

log = logging.getLogger("nuxiva.sync")


class Sync:
    def __init__(self, client, memory) -> None:
        self.client, self.memory = client, memory
        self.running = threading.Lock()

    def flush(self) -> int:
        if not self.running.acquire(blocking=False):
            return 0
        sent = 0
        try:
            while True:
                batch = self.memory.pending()
                if not batch:
                    return sent
                turns = [{"id": t["id"], "at": t["at"], "text": t["text"], "reply": t["reply"]} for t in batch]
                try:
                    self.client.request("/api/nodes/memory-sync", {"turns": turns}, timeout=20)
                except (ServerError, Unauthorized) as exc:
                    log.info("Sincronizzazione rimandata: %s", exc)
                    return sent
                self.memory.mark_synced([t["id"] for t in batch])
                sent += len(batch)
        finally:
            self.running.release()

    def flush_later(self) -> None:
        threading.Thread(target=self.flush, daemon=True, name="memory-sync").start()
