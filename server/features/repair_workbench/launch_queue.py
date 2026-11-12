import threading
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List

LAUNCH_TTL_SECONDS = 120.0
MAX_PENDING_PER_OWNER = 8


@dataclass(frozen=True)
class LaunchRequest:
    launch_id: str
    project_id: str
    created_at: float


class WorkbenchLaunchQueue:
    def __init__(self) -> None:
        self._items: Dict[str, List[LaunchRequest]] = {}
        self._lock = threading.Lock()

    def push(self, owner_id: str, project_id: str) -> LaunchRequest:
        request = LaunchRequest(uuid.uuid4().hex, project_id, time.time())
        with self._lock:
            items = self._fresh(owner_id)
            items.append(request)
            self._items[owner_id] = items[-MAX_PENDING_PER_OWNER:]
        return request

    def pending(self, owner_id: str, since: float) -> List[LaunchRequest]:
        with self._lock:
            items = self._fresh(owner_id)
            self._items[owner_id] = items
            return [item for item in items if item.created_at > since]

    def _fresh(self, owner_id: str) -> List[LaunchRequest]:
        cutoff = time.time() - LAUNCH_TTL_SECONDS
        return [i for i in self._items.get(owner_id, []) if i.created_at >= cutoff]


workbench_launch_queue = WorkbenchLaunchQueue()
