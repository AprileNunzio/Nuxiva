from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import packages
from config import read_env
from state import store
from steps import STEP_BY_ID, STEPS, Step, converge_step


class InstallManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._active_step: str = ""

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def status(self) -> Dict[str, Any]:
        return {
            "active_step": self._active_step,
            "installed_count": sum(1 for s in STEPS if (store.steps.get(s.id) or {}).get("status") == "done"),
            "total_steps": len(STEPS),
        }

    def is_wanted(self, step_id: str, env: Optional[Dict[str, str]] = None) -> bool:
        return packages.step_wanted(step_id, env)

    def wanted_background_steps(self, env: Optional[Dict[str, str]] = None) -> List[Step]:
        target_env = read_env() if env is None else env
        return [s for s in STEPS if s.background and packages.step_wanted(s.id, target_env)]

    async def run_step(self, step_id: str, force: bool = False) -> bool:
        step = STEP_BY_ID.get(step_id)
        if not step:
            raise KeyError(f"Step {step_id} not found")
        async with self._lock:
            self._active_step = step_id
            try:
                return await converge_step(step, force=force, quiet=True)
            finally:
                self._active_step = ""

    async def queue_step(self, step_id: str, priority: int = 50) -> bool:
        from background import queue
        return queue.prioritize(step_id)

    def snapshot(self) -> Dict[str, Any]:
        from background import queue
        return queue.snapshot()
