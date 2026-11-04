import logging
import threading
from typing import Any, Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Err, Ok, Result

logger = logging.getLogger("nuxiva.hippocampus.embedding")

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
PROBE_TEXT = "nuxiva"


class FastEmbedEngine:
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self._model: Any = None
        self._dimension = 0
        self._failure: Optional[CortexFailure] = None
        self._lock = threading.Lock()

    def _load(self) -> Result[None, CortexFailure]:
        try:
            from fastembed import TextEmbedding
        except ImportError:
            return fail("hippocampus.embedding.unavailable", model=self.model_name)
        try:
            model = TextEmbedding(model_name=self.model_name)
            probe = next(iter(model.embed([PROBE_TEXT])))
        except (OSError, ValueError, RuntimeError) as exc:
            logger.error("Embedding model %s could not be loaded (%s)", self.model_name, type(exc).__name__)
            return fail("hippocampus.embedding.failed", model=self.model_name)
        self._model = model
        self._dimension = len(probe)
        return Ok(None)

    def ensure_dimension(self) -> Result[int, CortexFailure]:
        with self._lock:
            if self._model is None:
                if self._failure is not None:
                    return Err(self._failure)
                loaded = self._load()
                if not loaded.is_ok:
                    self._failure = loaded.error
                    return loaded
            return Ok(self._dimension)

    def state(self) -> Result[Optional[int], CortexFailure]:
        with self._lock:
            if self._failure is not None:
                return Err(self._failure)
            return Ok(self._dimension if self._model is not None else None)

    def embed(self, text: str) -> Result[list[float], CortexFailure]:
        ready = self.ensure_dimension()
        if not ready.is_ok:
            return ready
        try:
            vector = next(iter(self._model.embed([text])))
        except (ValueError, RuntimeError) as exc:
            logger.error("Embedding computation failed (%s)", type(exc).__name__)
            return fail("hippocampus.embedding.failed", model=self.model_name)
        return Ok([float(value) for value in vector])
