import os
import threading
from pathlib import Path
from typing import Optional

from server.config.env import settings
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.skill_forge.auto import AutoForge
from server.core.skill_forge.forge import SkillForge, SkillRuntime
from server.core.skill_forge.misses import MissLedger
from server.core.skill_forge.store import SkillStore

STORAGE_FILE = Path("cortex") / "skills.sealed"
MISSES_FILE = Path("cortex") / "forge_requests.db"
AUTOFORGE_KEY = "NUXIVA_CORTEX_AUTOFORGE"
OFF = frozenset({"0", "off", "no", "false"})

_store: Optional[SkillStore] = None
_misses: Optional[MissLedger] = None
_auto: Optional[AutoForge] = None
_lock = threading.Lock()


def skill_store() -> SkillStore:
    global _store
    with _lock:
        if _store is None:
            _store = SkillStore(Path(settings.DATA_DIR) / STORAGE_FILE, ZeroTrustVault(lambda: settings.NUXIVA_SECRET_KEY))
        return _store


def skill_runtime() -> SkillRuntime:
    return SkillRuntime(skill_store())


def skill_forge() -> SkillForge:
    from server.core.hippocampus_router.composition import hippocampus_service
    return SkillForge(hippocampus_service(), skill_store())


def miss_ledger() -> MissLedger:
    global _misses
    with _lock:
        if _misses is None:
            _misses = MissLedger(Path(settings.DATA_DIR) / MISSES_FILE, ZeroTrustVault(lambda: settings.NUXIVA_SECRET_KEY))
        return _misses


def autoforge_enabled() -> bool:
    return os.environ.get(AUTOFORGE_KEY, "1").strip().lower() not in OFF


def auto_forge() -> AutoForge:
    global _auto
    from server.core.hippocampus_router.composition import hippocampus_service
    from server.features.skill_synthesis.composition import complete
    ledger = miss_ledger()
    with _lock:
        if _auto is None:
            _auto = AutoForge(SkillForge(hippocampus_service(), skill_store()), hippocampus_service(), ledger, complete)
        return _auto
