from __future__ import annotations

import logging
from typing import Any, Dict
from agenti.auto_update.self_healing import self_healer
from os_notification import notification_manager

log = logging.getLogger("nuxiva.os.boot_updater")


class BootUpdater:
    def __init__(self) -> None:
        self._last_result: Dict[str, Any] = {}

    async def execute_boot_check(self) -> Dict[str, Any]:
        healing_result = self_healer.run_all()

        try:
            import updater
            if not updater.auto_update_enabled():
                self._last_result = {
                    "ok": True,
                    "applied": False,
                    "reason": "disabled",
                    "healing": healing_result,
                }
                return self._last_result

            updated = await updater.priority_update("prioritario all'avvio")
            if updated:
                notification_manager.notify(
                    level="INFO",
                    code="os_boot_update",
                    label_key="os_update_boot_applied",
                    message="Aggiornamento autoriparante applicato all'avvio",
                    action={"appId": "features_hub"},
                    force=True,
                )
            self._last_result = {
                "ok": True,
                "applied": updated,
                "healing": healing_result,
            }
            return self._last_result
        except Exception as exc:
            log.warning("Verifica aggiornamenti all'avvio fallita: %s", exc)
            self._last_result = {
                "ok": False,
                "error": str(exc),
                "healing": healing_result,
            }
            return self._last_result

    def last_status(self) -> Dict[str, Any]:
        return self._last_result


boot_updater = BootUpdater()
