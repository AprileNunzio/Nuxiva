from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional
from os_notification import notification_manager

log = logging.getLogger("nuxiva.os.process")


class ProcessDescriptor:
    def __init__(self, name: str, runner: Callable[[], Coroutine[Any, Any, None] | None], interval: float = 0.0) -> None:
        self.name = name
        self.runner = runner
        self.interval = interval
        self.status = "stopped"
        self.restarts = 0
        self.last_start = 0.0
        self.last_error: Optional[str] = None
        self.task: Optional[asyncio.Task] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "restarts": self.restarts,
            "last_start": self.last_start,
            "last_error": self.last_error,
            "interval": self.interval,
        }


class ProcessManager:
    def __init__(self) -> None:
        self._descriptors: Dict[str, ProcessDescriptor] = {}

    def register(self, name: str, runner: Callable[[], Any], interval: float = 0.0) -> None:
        self._descriptors[name] = ProcessDescriptor(name, runner, interval)

    def get_all(self) -> List[Dict[str, Any]]:
        return [desc.to_dict() for desc in self._descriptors.values()]

    def spawn(self, name: str) -> Optional[asyncio.Task]:
        desc = self._descriptors.get(name)
        if not desc:
            return None

        desc.task = asyncio.create_task(self._supervise(desc), name=f"proc_{name}")
        return desc.task

    async def _supervise(self, desc: ProcessDescriptor) -> None:
        while True:
            desc.status = "running"
            desc.last_start = time.time()
            try:
                res = desc.runner()
                if asyncio.iscoroutine(res):
                    await res
                if desc.interval > 0:
                    await asyncio.sleep(desc.interval)
                else:
                    desc.status = "completed"
                    break
            except asyncio.CancelledError:
                desc.status = "stopped"
                break
            except Exception as exc:
                desc.restarts += 1
                desc.status = "crashed"
                desc.last_error = str(exc)
                log.error("Processo OS '%s' terminato con errore: %s", desc.name, exc)
                notification_manager.notify(
                    level="WARNING",
                    code=f"proc_crash_{desc.name}",
                    label_key="os_process_failed",
                    message=f"Il processo '{desc.name}' è fallito: {exc}",
                    details={"name": desc.name, "restarts": desc.restarts, "error": str(exc)},
                    action={"appId": "features_hub"},
                )
                await asyncio.sleep(min(30.0, 2.0 ** min(desc.restarts, 4)))


process_manager = ProcessManager()
