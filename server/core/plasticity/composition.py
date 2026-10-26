import asyncio
import threading
from pathlib import Path
from typing import Optional

from server.config.env import settings
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.hippocampus_router.composition import hippocampus_service
from server.core.plasticity.ledger import PlasticityLedger
from server.core.plasticity.service import PlasticityService
from server.core.plasticity.auto_training import AutoTrainer
from server.core.core_platform.result import Result
from server.core.plasticity.scheduler import NightTask
from server.core.skill_forge.composition import auto_forge, autoforge_enabled, miss_ledger, skill_forge, skill_store

LEDGER_FILE = Path("cortex") / "plasticity.db"
MISS_RETENTION_DAYS = 30.0

_service: Optional[PlasticityService] = None
_trainer: Optional[AutoTrainer] = None
_ledger: Optional[PlasticityLedger] = None
_lock = threading.Lock()


def _manual_skills() -> frozenset[str]:
    listing = skill_store().listing()
    return frozenset(item["neuron_id"] for item in listing.value if item["origin"] == "manual") if listing.is_ok else frozenset()


def plasticity_ledger() -> PlasticityLedger:
    global _ledger
    with _lock:
        if _ledger is None:
            _ledger = PlasticityLedger(Path(settings.DATA_DIR) / LEDGER_FILE, ZeroTrustVault(lambda: settings.NUXIVA_SECRET_KEY))
        return _ledger


def plasticity_service() -> PlasticityService:
    global _service
    ledger = plasticity_ledger()
    with _lock:
        if _service is None:
            _service = PlasticityService(hippocampus_service(), ledger, lambda neuron_id: neuron_id in _manual_skills(),
                                         lambda neuron_id: skill_forge().retire(neuron_id))
        return _service


def auto_trainer() -> AutoTrainer:
    global _trainer
    ledger = plasticity_ledger()
    with _lock:
        if _trainer is None:
            _trainer = AutoTrainer(ledger, Path(settings.DATA_DIR))
        return _trainer


async def _forge_requests() -> Result:
    return await auto_forge().cycle()


async def _training() -> Result:
    return await auto_trainer().cycle()


async def _expire_requests() -> Result:
    return await asyncio.to_thread(miss_ledger().expire, MISS_RETENTION_DAYS)


def night_tasks() -> list[NightTask]:
    tasks: list[NightTask] = [("expire_requests", _expire_requests)]
    if autoforge_enabled():
        tasks.append(("skill_forge", _forge_requests))
    tasks.append(("training", _training))
    return tasks
