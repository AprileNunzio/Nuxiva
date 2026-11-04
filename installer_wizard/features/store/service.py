from __future__ import annotations

import logging
import psutil
from typing import Any

from features.store.catalog import find_item, get_catalog_with_status
from features.store.repositories import (
    find_custom_package,
    get_custom_packages,
    set_custom_package_installed,
)
from settings import apply_config

log = logging.getLogger("nuxiva.store")


class StoreManagerService:
    @staticmethod
    def list_all() -> list[dict[str, Any]]:
        official = get_catalog_with_status()
        custom = get_custom_packages()
        return official + custom

    @staticmethod
    def verify_resource_budget(item_id: str, force: bool = False) -> tuple[bool, str]:
        item = find_item(item_id)
        size_gb = item.size_gb if item else None
        if item is None:
            custom_pkg = find_custom_package(item_id)
            if custom_pkg:
                size_gb = float(custom_pkg.get("size_gb", 0.5))
            else:
                return False, "package_not_found"

        disk_free_gb = psutil.disk_usage("/").free / (1024**3)
        if disk_free_gb < size_gb * 1.25:
            return False, "insufficient_disk_space"

        mem_total_gb = psutil.virtual_memory().total / (1024**3)
        if size_gb >= 5.0 and mem_total_gb < 7.5:
            if not force:
                return False, "insufficient_memory"

        return True, "ok"

    @classmethod
    async def install_package(cls, item_id: str, user: str, force: bool = False) -> dict[str, Any]:
        item = find_item(item_id)
        if not item:
            custom_pkg = find_custom_package(item_id)
            if not custom_pkg:
                return {"ok": False, "error": "package_not_found"}
            budget_ok, reason = cls.verify_resource_budget(item_id, force=force)
            if not budget_ok:
                return {"ok": False, "error": reason}
            set_custom_package_installed(item_id, True)
            return {"ok": True, "applying": False, "id": item_id, "custom": True}

        budget_ok, reason = cls.verify_resource_budget(item_id, force=force)
        if not budget_ok:
            if reason == "insufficient_memory":
                mem_total_gb = round(psutil.virtual_memory().total / (1024**3), 1)
                return {
                    "ok": False,
                    "advisory": True,
                    "can_force": True,
                    "error": "insufficient_memory",
                    "ram_total_gb": mem_total_gb,
                    "recommended_ram_gb": 8.0,
                    "message": (
                        f"Il budget di memoria fisica dell'host ({mem_total_gb} GB rilevati) e inferiore alla soglia consigliata (8.0 GB) "
                        "per garantire la piena fluidita di questo modello neurale in concorrenza con gli altri sottosistemi di Nuxiva OS. "
                        "E possibile autorizzare l'allocazione forzata per consentire l'esecuzione con gestione ottimizzata dello swap."
                    ),
                }
            return {"ok": False, "error": reason}

        updates = {item.env_key: "1"}
        steps = list(item.steps)
        try:
            applying = await apply_config(updates, user, steps)
            return {"ok": True, "applying": applying, "id": item_id}
        except Exception as exc:
            log.error("Installazione pacchetto store fallita (%s): %s", item_id, exc)
            return {"ok": False, "error": str(exc)}

    @classmethod
    async def uninstall_package(cls, item_id: str, user: str) -> dict[str, Any]:
        item = find_item(item_id)
        if not item:
            custom_pkg = find_custom_package(item_id)
            if not custom_pkg:
                return {"ok": False, "error": "package_not_found"}
            set_custom_package_installed(item_id, False)
            return {"ok": True, "applying": False, "id": item_id, "custom": True}

        if not item.removable:
            return {"ok": False, "error": "package_not_removable"}

        updates = {item.env_key: "0"}
        steps = list(item.steps)
        try:
            applying = await apply_config(updates, user, steps)
            return {"ok": True, "applying": applying, "id": item_id}
        except Exception as exc:
            log.error("Disinstallazione pacchetto store fallita (%s): %s", item_id, exc)
            return {"ok": False, "error": str(exc)}


store_service = StoreManagerService()
