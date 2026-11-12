from __future__ import annotations

import asyncio
import logging
import psutil
from typing import Any, Dict, List
from os_notification import notification_manager

try:
    from nuxiva_native import RustAdminOsMemory  # type: ignore
except ImportError:
    RustAdminOsMemory = None  # type: ignore

log = logging.getLogger("nuxiva.os.memory")


class MemoryManager:
    def __init__(
        self,
        warn_percent: float = 85.0,
        critical_percent: float = 92.0,
        min_free_mb: float = 800.0,
        recovery_percent: float = 75.0,
    ) -> None:
        self.warn_percent = warn_percent
        self.critical_percent = critical_percent
        self.min_free_mb = min_free_mb
        self.recovery_percent = recovery_percent
        self._current_state = "normal"
        self._throttled = False
        self._last_sample: Dict[str, Any] = {}
        if RustAdminOsMemory is not None:
            self._rust_engine = RustAdminOsMemory(
                warning_percent=warn_percent,
                critical_percent=critical_percent,
                critical_min_available_bytes=int(min_free_mb * 1024 * 1024),
                warning_consecutive_threshold=3,
            )
        else:
            self._rust_engine = None

    def sample(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        total_mb = round(mem.total / (1024 * 1024), 1)
        available_mb = round(mem.available / (1024 * 1024), 1)
        used_mb = round((mem.total - mem.available) / (1024 * 1024), 1)
        percent = mem.percent

        if self._rust_engine is not None:
            state, throttled, _ = self._rust_engine.evaluate(mem.total, mem.available)
            self._throttled = throttled
        else:
            state = "normal"
            if percent >= self.critical_percent or available_mb < (self.min_free_mb / 2):
                state = "critical"
            elif percent >= self.warn_percent or available_mb < self.min_free_mb:
                state = "warning"
            elif percent <= self.recovery_percent and self._current_state != "normal":
                state = "normal"

        self._handle_state_transition(state, percent, available_mb)
        self._current_state = state

        top_procs = self._get_top_processes(limit=5)
        self._last_sample = {
            "total_mb": total_mb,
            "used_mb": used_mb,
            "available_mb": available_mb,
            "percent": percent,
            "swap_percent": swap.percent,
            "state": state,
            "throttled": self._throttled,
            "top_processes": top_procs,
        }
        return self._last_sample

    def _handle_state_transition(self, state: str, percent: float, free_mb: float) -> None:
        if state == "critical" and self._current_state != "critical":
            self._throttled = True
            notification_manager.notify(
                level="CRITICAL",
                code="os_ram_critical",
                label_key="os_ram_critical_oom_risk",
                message=f"Memoria RAM critica: {percent}% in uso ({free_mb} MB liberi)",
                details={"used_percent": percent, "free_mb": free_mb, "throttled": True},
                action={"appId": "features_hub"},
                force=True,
            )
        elif state == "warning" and self._current_state == "normal":
            notification_manager.notify(
                level="WARNING",
                code="os_ram_warning",
                label_key="os_ram_high_pressure",
                message=f"Consumo di memoria RAM elevato: {percent}% in uso ({free_mb} MB liberi)",
                details={"used_percent": percent, "free_mb": free_mb},
                action={"appId": "features_hub"},
            )
        elif state == "normal" and self._current_state != "normal":
            self._throttled = False

    def _get_top_processes(self, limit: int = 5) -> List[Dict[str, Any]]:
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = p.info
                mem_info = info.get("memory_info")
                rss_mb = round((mem_info.rss / (1024 * 1024)), 1) if mem_info else 0.0
                procs.append({
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "rss_mb": rss_mb,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x["rss_mb"], reverse=True)
        return procs[:limit]

    def is_throttled(self) -> bool:
        if self._rust_engine is not None:
            return self._rust_engine.is_throttled()
        return self._throttled

    async def run(self, interval_s: float = 10.0) -> None:
        while True:
            try:
                self.sample()
            except Exception as exc:
                log.error("Errore nel ciclo di monitoraggio memoria OS: %s", exc)
            await asyncio.sleep(interval_s)


memory_manager = MemoryManager()
