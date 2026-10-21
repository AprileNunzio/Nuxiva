import hashlib
import hmac
import json
import logging
import math
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping

logger = logging.getLogger("nuxiva.semantic_cache")
MAX_TTL_SECONDS = 3600.0
MAX_VECTOR_DIMENSIONS = 4096
PAYLOAD_KEYS = {"agent_id", "speech_output", "result_data", "value", "unit", "explanation", "source_hash"}
VALUE_KEYS = {"value", "unit", "explanation", "source_hash"}
DYNAMIC_PRODUCERS = {"home_assistant", "browser_agent", "whiteboard", "system2_latent_engine", "nuxiva_conversation",
                     "media_player", "system_core", "orchestrator_planner"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any, secret: str) -> str:
    encoded = canonical(value)
    if len(encoded) > 262144:
        raise ValueError("Cache scope exceeds configured limit")
    return hmac.new(secret.encode("utf-8"), b"nuxiva.semantic-cache.scope.v2\0" + encoded, hashlib.sha256).hexdigest()


def safe_payload(result: dict) -> bool:
    if not isinstance(result, dict) or not result or set(result) - PAYLOAD_KEYS:
        return False
    if any(key in result and not isinstance(result[key], str) for key in ("agent_id", "speech_output")):
        return False
    if result.get("agent_id") in DYNAMIC_PRODUCERS:
        return False
    values = result.get("result_data", {})
    if not isinstance(values, dict) or set(values) - VALUE_KEYS:
        return False
    for value in [result.get(k) for k in VALUE_KEYS] + list(values.values()):
        if isinstance(value, (dict, list, tuple)):
            return False
    try:
        return len(canonical(result)) <= 32768
    except (TypeError, ValueError, OverflowError):
        return False


def unit_vector(values) -> list[float] | None:
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= MAX_VECTOR_DIMENSIONS:
        return None
    try:
        if any(isinstance(v, bool) for v in values):
            return None
        vector = [float(v) for v in values]
        if not all(math.isfinite(v) for v in vector):
            return None
        scale = max(abs(v) for v in vector)
        if scale == 0:
            return None
        vector = [v / scale for v in vector]
        norm = math.sqrt(sum(v * v for v in vector))
        return [v / norm for v in vector]
    except (ValueError, TypeError, OverflowError):
        return None


@dataclass(frozen=True)
class CacheScope:
    user_id: str
    device_id: str
    context: Mapping[str, Any]
    revision: str

    def fingerprint(self, secret: str) -> str:
        if not all(isinstance(v, str) and v.strip() for v in (self.user_id, self.device_id, self.revision)):
            raise ValueError("Cache scope requires identity, device and context revision")
        if not isinstance(self.context, Mapping):
            raise ValueError("Cache scope requires a context snapshot")
        return digest({"user": self.user_id, "device": self.device_id, "revision": self.revision,
                       "context": dict(self.context)}, secret)


@dataclass(frozen=True)
class PureResultPolicy:
    policy_id: str
    verifier: Callable[[str, dict, Mapping[str, Any]], bool]
    ttl_seconds: float = 300.0
    allow_semantic: bool = False

    def __post_init__(self):
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,80}", self.policy_id) or not callable(self.verifier):
            raise ValueError("A pure cache policy requires an explicit code verifier")
        if isinstance(self.ttl_seconds, bool) or not math.isfinite(self.ttl_seconds) or not 0 < self.ttl_seconds <= MAX_TTL_SECONDS:
            raise ValueError("Invalid pure result cache TTL")

    def accepts(self, query: str, result: dict, context: Mapping[str, Any]) -> bool:
        if not safe_payload(result):
            return False
        try:
            return self.verifier(query, deepcopy(result), deepcopy(dict(context))) is True
        except Exception as exc:
            logger.warning("Pure cache verification failed (%s)", type(exc).__name__)
            return False
