from __future__ import annotations

from typing import Any, Dict

from agenti.services.download_manager import DownloadManager
from agenti.services.install_manager import InstallManager
from os_notification import notification_manager


class UpdateManagerWrapper:
    def __init__(self) -> None:
        pass

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    def status(self) -> Dict[str, Any]:
        import updater
        return {
            "branch": updater.branch(),
        }

    async def check_updates(self) -> Dict[str, Any]:
        from features.settings.auto_update import auto_update_service
        return await auto_update_service.check_online_updates()

    async def apply_update(self, version: str) -> bool:
        from features.settings.auto_update import auto_update_service
        return await auto_update_service.apply_update_now(version)


class CommandCenter:
    def __init__(self) -> None:
        self.downloads = DownloadManager()
        self.installs = InstallManager()
        self.notifications = notification_manager
        self.updates = UpdateManagerWrapper()

    async def initialize(self) -> None:
        await self.downloads.initialize()
        await self.installs.initialize()
        await self.updates.initialize()

    async def shutdown(self) -> None:
        await self.downloads.shutdown()
        await self.installs.shutdown()
        await self.updates.shutdown()

    def overview(self) -> Dict[str, Any]:
        return {
            "downloads": self.downloads.status(),
            "installs": self.installs.status(),
            "notifications": {
                "count": len(self.notifications.get_all()),
            },
            "updates": self.updates.status(),
        }


command_center = CommandCenter()
