import os
import asyncio
from typing import Dict, List, Callable, Coroutine, Any
from server.core.scanner.universal_scanner import UniversalScanner

class DirectoryWatcher:
    def __init__(self, check_interval_seconds: float = 2.0) -> None:
        self.check_interval_seconds = check_interval_seconds
        self._scanners: Dict[str, UniversalScanner] = {}
        self._listeners: List[Callable[[str, str, Dict[str, Any]], Coroutine[Any, Any, None]]] = []
        self._running = False
        self._task: asyncio.Task = None

    def register_scanner(self, name: str, scanner: UniversalScanner) -> None:
        self._scanners[name] = scanner

    def subscribe(self, listener: Callable[[str, str, Dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        self._listeners.append(listener)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _watch_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.check_interval_seconds)
                for name, scanner in list(self._scanners.items()):
                    before_keys = set(scanner._cache.keys())
                    items = scanner.scan_all(force=False)
                    after_keys = set(items.keys())
                    added = after_keys - before_keys
                    removed = before_keys - after_keys

                    if added or removed:
                        event_payload = {
                            "added": list(added),
                            "removed": list(removed),
                            "total": len(items),
                            "items": [m.model_dump() for m in scanner.get_manifests()],
                        }
                        for listener in self._listeners:
                            try:
                                await listener(name, "change", event_payload)
                            except Exception:
                                pass
            except asyncio.CancelledError:
                break
            except Exception:
                pass

registry_watcher = DirectoryWatcher()
