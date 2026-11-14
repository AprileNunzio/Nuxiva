import re
import threading
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from collections.abc import Mapping

import native_core

_DURATION = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smhd]?)\s*$", re.I)


def _integer(value: str, minimum: int) -> int | None:
    try:
        return max(minimum, int(float(value)))
    except (TypeError, ValueError, OverflowError):
        return None


@dataclass
class ModelRate:
    remaining_requests: int | None = None
    request_limit: int | None = None
    remaining_tokens: int | None = None
    reset_at: float = 0.0
    cooldown_until: float = 0.0
    disabled: bool = False
    ttft_ms: float = 0.0
    tokens_per_second: float = 0.0


_native = None
_lock = threading.Lock()


def _engine():
    global _native
    if _native is None:
        with _lock:
            if _native is None:
                factory = native_core.symbol("RustRateRules")
                _native = factory() if factory is not None else False
    return _native or None


def _state(rate: "ModelRate") -> tuple:
    return (rate.remaining_requests, rate.request_limit, rate.remaining_tokens, float(rate.reset_at),
            float(rate.cooldown_until), bool(rate.disabled))


class RateLimiter:
    def __init__(self) -> None:
        self._rates: dict[tuple[str, str], ModelRate] = {}

    def _rate(self, provider: str, model: str) -> ModelRate:
        return self._rates.setdefault((provider, model), ModelRate())

    def clear(self, provider: str) -> None:
        self._rates = {key: value for key, value in self._rates.items() if key[0] != provider}

    @staticmethod
    def _reset_value(value: str, now: float) -> float:
        match = _DURATION.match(value)
        if match:
            scale = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[match.group(2).lower()]
            return now + float(match.group(1)) * scale
        try:
            parsed = parsedate_to_datetime(value).timestamp()
            return parsed if parsed > now else now
        except (TypeError, ValueError, OverflowError):
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return now
            return numeric if numeric > now else now + numeric

    def observe(self, provider: str, model: str, headers: Mapping[str, str], status: int = 200, now: float | None = None) -> ModelRate:
        current = time.time() if now is None else now
        engine = _engine()
        if engine is None:
            native_core.python_fallback("brain.rate_limiter")
            return self._py_observe(provider, model, headers, status, current)
        rate = self._rate(provider, model)
        try:
            pairs = [(str(key), str(value)) for key, value in headers.items()]
            kind, state = engine.observe(_state(rate), pairs, int(status), float(current))
        except (ValueError, TypeError, OverflowError):
            return self._py_observe(provider, model, headers, status, current)
        if kind != "rate":
            return self._py_observe(provider, model, headers, status, current)
        (rate.remaining_requests, rate.request_limit, rate.remaining_tokens, rate.reset_at, rate.cooldown_until,
         rate.disabled) = state
        return rate

    def _py_observe(self, provider: str, model: str, headers: Mapping[str, str], status: int, current: float) -> ModelRate:
        normalized = {str(key).lower(): str(value).strip() for key, value in headers.items()}
        rate = self._rate(provider, model)
        for name, attr in (("x-ratelimit-remaining-requests", "remaining_requests"),
                           ("x-ratelimit-remaining-tokens", "remaining_tokens"),
                           ("x-ratelimit-remaining", "remaining_requests")):
            if name in normalized:
                parsed = _integer(normalized[name], 0)
                if parsed is not None:
                    setattr(rate, attr, parsed)
        for name in ("x-ratelimit-limit-requests", "x-ratelimit-limit"):
            if name in normalized:
                parsed = _integer(normalized[name], 1)
                if parsed is not None:
                    rate.request_limit = parsed
        reset = normalized.get("retry-after") or normalized.get("x-ratelimit-reset-requests") or normalized.get("x-ratelimit-reset")
        if reset:
            rate.reset_at = self._reset_value(reset, current)
        if status == 429:
            rate.cooldown_until = rate.reset_at if rate.reset_at > current else current + 60
        elif status in (401, 403):
            rate.disabled = True
        elif status >= 500:
            rate.cooldown_until = max(rate.cooldown_until, current + 120)
        return rate

    def available(self, provider: str, model: str, estimated_tokens: int = 0, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        rate = self._rate(provider, model)
        engine = _engine()
        if engine is not None:
            try:
                return engine.available(_state(rate), int(estimated_tokens), float(current))
            except (ValueError, TypeError, OverflowError):
                pass
        return self._py_available(rate, estimated_tokens, current)

    @staticmethod
    def _py_available(rate: ModelRate, estimated_tokens: int, current: float) -> bool:
        if rate.disabled or rate.cooldown_until > current:
            return False
        if rate.remaining_requests is not None and rate.remaining_requests <= 1 and rate.reset_at > current:
            return False
        if rate.remaining_tokens is not None and rate.remaining_tokens < estimated_tokens and rate.reset_at > current:
            return False
        return True

    def cooldown_seconds(self, provider: str, model: str, now: float | None = None) -> int:
        current = time.time() if now is None else now
        return max(0, int(self._rate(provider, model).cooldown_until - current))

    def metrics(self) -> dict[str, dict]:
        now = time.time()
        return {model: {"remaining_requests": rate.remaining_requests, "remaining_tokens": rate.remaining_tokens,
                        "quota_pct": (round(100 * rate.remaining_requests / rate.request_limit) if rate.remaining_requests is not None and rate.request_limit else 0), "ttft_ms": rate.ttft_ms,
                        "tokens_per_second": rate.tokens_per_second,
                        "cooldown_seconds": max(0, int(rate.cooldown_until - now)), "disabled": rate.disabled}
                for (provider, model), rate in self._rates.items()}


rate_limiter = RateLimiter()
