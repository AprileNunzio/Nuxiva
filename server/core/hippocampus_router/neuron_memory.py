import threading
from typing import Any, Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.native_bridge import call_native
from server.core.core_platform.result import Ok, Result
from server.core.hippocampus_router.neuron_repository import EncryptedNeuronRepository


class NeuronMemory:
    def __init__(self, repository: EncryptedNeuronRepository) -> None:
        self._repository = repository
        self._index: Any = None
        self._storage_error: Optional[CortexFailure] = None
        self._lock = threading.RLock()

    def _fresh(self, dimension: int) -> Result[Any, CortexFailure]:
        return call_native(lambda native: native.RustNeuronIndex(dimension))

    def _restore(self, snapshot: str, dimension: int) -> Result[Any, CortexFailure]:
        restored = call_native(lambda native: native.RustNeuronIndex.from_snapshot_json(snapshot))
        if restored.is_ok and restored.value.dimension() != dimension:
            return fail("cortex.vector.dimension_mismatch")
        return restored

    def _open(self, dimension: int) -> Result[Any, CortexFailure]:
        loaded = self._repository.load()
        if not loaded.is_ok:
            self._storage_error = loaded.error
            return self._fresh(dimension)
        if loaded.value is None:
            return self._fresh(dimension)
        restored = self._restore(loaded.value, dimension)
        if restored.is_ok:
            return restored
        self._storage_error = restored.error
        return self._fresh(dimension)

    def index(self, dimension: int) -> Result[Any, CortexFailure]:
        with self._lock:
            if self._index is None:
                opened = self._open(dimension)
                if not opened.is_ok:
                    return opened
                self._index = opened.value
            if self._index.dimension() != dimension:
                return fail("cortex.vector.dimension_mismatch")
            return Ok(self._index)

    def persist(self) -> Result[None, CortexFailure]:
        with self._lock:
            if self._index is None:
                return Ok(None)
            if self._storage_error is not None:
                return fail(self._storage_error.code)
            snapshot = call_native(lambda native: self._index.snapshot_json())
            if not snapshot.is_ok:
                return snapshot
            return self._repository.save(snapshot.value)

    @property
    def storage_error(self) -> Optional[CortexFailure]:
        return self._storage_error

    def neuron_count(self) -> int:
        with self._lock:
            return len(self._index) if self._index is not None else 0
