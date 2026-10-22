import threading
from pathlib import Path
from typing import Optional

from server.config.env import settings
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.skill_forge.forge import SkillForge, SkillRuntime
from server.core.skill_forge.store import SkillStore

STORAGE_FILE = Path("cortex") / "skills.sealed"

_store: Optional[SkillStore] = None
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
