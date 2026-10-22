import os
import threading
from pathlib import Path
from typing import Optional

from server.config.env import settings
from server.core.core_platform.zero_trust_crypto import ZeroTrustVault
from server.core.hippocampus_router.contracts import ArbiterThresholds
from server.core.hippocampus_router.hippocampus_service import HippocampusService
from server.core.hippocampus_router.neuron_memory import NeuronMemory
from server.core.hippocampus_router.neuron_repository import EncryptedNeuronRepository
from server.core.hippocampus_router.onnx_embedding_engine import DEFAULT_MODEL, FastEmbedEngine

STORAGE_FILE = Path("cortex") / "neurons.sealed"
MODEL_ENVIRONMENT_KEY = "NUXIVA_CORTEX_EMBED_MODEL"

_service: Optional[HippocampusService] = None
_lock = threading.Lock()


def build_service() -> HippocampusService:
    vault = ZeroTrustVault(lambda: settings.NUXIVA_SECRET_KEY)
    repository = EncryptedNeuronRepository(Path(settings.DATA_DIR) / STORAGE_FILE, vault)
    embedder = FastEmbedEngine(os.environ.get(MODEL_ENVIRONMENT_KEY, DEFAULT_MODEL))
    return HippocampusService(embedder, NeuronMemory(repository), ArbiterThresholds())


def hippocampus_service() -> HippocampusService:
    global _service
    with _lock:
        if _service is None:
            _service = build_service()
        return _service
