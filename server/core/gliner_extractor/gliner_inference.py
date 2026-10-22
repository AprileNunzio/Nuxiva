import logging
import threading
from typing import Any, Mapping, Optional, Sequence

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Err, Ok, Result

logger = logging.getLogger("nuxiva.gliner")

DEFAULT_MODEL = "urchade/gliner_multi-v2.1"
DEFAULT_THRESHOLD = 0.5


class GlinerSlotExtractor:
    def __init__(self, model_name: str = DEFAULT_MODEL, threshold: float = DEFAULT_THRESHOLD) -> None:
        self.model_name = model_name
        self._threshold = threshold
        self._model: Any = None
        self._failure: Optional[CortexFailure] = None
        self._lock = threading.Lock()

    def _load(self) -> Result[Any, CortexFailure]:
        with self._lock:
            if self._model is not None:
                return Ok(self._model)
            if self._failure is not None:
                return Err(self._failure)
            try:
                from gliner import GLiNER
            except ImportError:
                self._failure = CortexFailure("gliner.unavailable")
                return Err(self._failure)
            try:
                self._model = GLiNER.from_pretrained(self.model_name)
            except (OSError, ValueError, RuntimeError) as exc:
                logger.error("GLiNER model %s could not be loaded (%s)", self.model_name, type(exc).__name__)
                self._failure = CortexFailure("gliner.unavailable")
                return Err(self._failure)
            return Ok(self._model)

    def extract(self, utterance: str, schema: Sequence[Mapping[str, Any]]) -> Result[dict[str, str], CortexFailure]:
        loaded = self._load()
        if not loaded.is_ok:
            return loaded
        labels = [str(definition["entity_label"]) for definition in schema]
        try:
            entities = loaded.value.predict_entities(utterance, labels, threshold=self._threshold)
        except (ValueError, RuntimeError, KeyError) as exc:
            logger.error("GLiNER inference failed (%s)", type(exc).__name__)
            return fail("gliner.inference_failed")
        return Ok(self._assign(schema, entities))

    @staticmethod
    def _assign(schema: Sequence[Mapping[str, Any]], entities: Sequence[Mapping[str, Any]]) -> dict[str, str]:
        assigned: dict[str, str] = {}
        for definition in schema:
            candidates = [e for e in entities if e.get("label") == definition["entity_label"]]
            if candidates:
                best = max(candidates, key=lambda entity: float(entity.get("score", 0.0)))
                assigned[str(definition["name"])] = str(best["text"])
        return assigned
