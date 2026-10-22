import threading
from pathlib import Path
from typing import Optional

from server.config.env import settings
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.hippocampus_router.composition import hippocampus_service
from server.core.plasticity.ledger import PlasticityLedger
from server.core.plasticity.service import PlasticityService
from server.core.skill_forge.composition import skill_store

LEDGER_FILE = Path("cortex") / "plasticity.db"

_service: Optional[PlasticityService] = None
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
            _service = PlasticityService(hippocampus_service(), ledger, lambda neuron_id: neuron_id in _manual_skills())
        return _service
