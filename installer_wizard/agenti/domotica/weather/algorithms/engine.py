import json
import logging
import os

from agenti.weather.algorithms import insights as py_insights
from agenti.weather.algorithms import verify as py_verify

log = logging.getLogger("nuxiva.weather.engine")


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "weather_insights") else None


def verify(forecasts: list[dict], observed: list[dict], lead: int | None = None, min_pairs: int = 0) -> dict:
    native = _native()
    if native is not None:
        try:
            body = {"forecasts": forecasts, "observed": observed, "lead": lead, "min_pairs": max(0, int(min_pairs))}
            return json.loads(native.weather_verify(json.dumps(body)))
        except ValueError as exc:
            log.info("verifica nativa non riuscita (%s), uso Python", type(exc).__name__)
    return py_verify.verify(forecasts, observed, lead, min_pairs)


def insights(situation: dict) -> list[dict]:
    native = _native()
    if native is not None:
        try:
            return json.loads(native.weather_insights(json.dumps(situation)))
        except ValueError as exc:
            log.info("avvisi nativi non riusciti (%s), uso Python", type(exc).__name__)
    return py_insights.insights(situation)
