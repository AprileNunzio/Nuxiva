from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol


class IServiceManager(Protocol):
    def status(self) -> Dict[str, Any]:
        ...

    async def initialize(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...


class IDownloadManager(IServiceManager, Protocol):
    async def download(
        self,
        url: str,
        destination: str,
        on_progress: Optional[Callable[[int, float, str], None]] = None,
        timeout_s: float = 600.0,
    ) -> bool:
        ...

    def cancel(self, download_id: str) -> bool:
        ...

    def active_downloads(self) -> List[Dict[str, Any]]:
        ...


class IInstallManager(IServiceManager, Protocol):
    async def queue_step(self, step_id: str, priority: int = 50) -> bool:
        ...

    async def run_step(self, step_id: str, force: bool = False) -> bool:
        ...

    def is_wanted(self, step_id: str, env: Optional[Dict[str, str]] = None) -> bool:
        ...

    def snapshot(self) -> Dict[str, Any]:
        ...


class INotificationManager(IServiceManager, Protocol):
    def notify(
        self,
        level: str,
        code: str,
        label_key: str,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        action: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> Optional[Any]:
        ...

    def get_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        ...


class IUpdateManager(IServiceManager, Protocol):
    async def check_updates(self) -> Dict[str, Any]:
        ...

    async def apply_update(self, version: str) -> bool:
        ...
