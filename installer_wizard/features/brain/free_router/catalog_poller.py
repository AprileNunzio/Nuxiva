import asyncio
import re
import time
from decimal import Decimal, InvalidOperation

import httpx

CATALOG_URL = "https://openrouter.ai/api/v1/models"
REFRESH_SECONDS = 6 * 60 * 60
_rows: list[dict] = []
_updated_at = 0.0
_lock = asyncio.Lock()
_MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:+-]{0,199}$")


def _context_length(value: object) -> int:
    try:
        return max(0, min(2_000_000, int(value or 0)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _zero_price(value: object) -> bool:
    try:
        return Decimal(str(value)) == 0
    except (InvalidOperation, TypeError, ValueError):
        return False


def normalize_model(model: dict) -> dict | None:
    pricing = model.get("pricing")
    if not isinstance(pricing, dict) or not _zero_price(pricing.get("prompt")) or not _zero_price(pricing.get("completion")):
        return None
    model_id = model.get("id")
    if not isinstance(model_id, str) or not _MODEL_ID.fullmatch(model_id):
        return None
    architecture = model.get("architecture") if isinstance(model.get("architecture"), dict) else {}
    modalities = architecture.get("input_modalities") if isinstance(architecture.get("input_modalities"), list) else []
    parameters = model.get("supported_parameters") if isinstance(model.get("supported_parameters"), list) else []
    return {
        "id": model_id,
        "name": str(model.get("name") or model_id)[:120],
        "context": _context_length(model.get("context_length")),
        "vision": "image" in modalities,
        "tools": "tools" in parameters or "tool_choice" in parameters,
        "json": "response_format" in parameters,
        "reasoning": "reasoning" in parameters,
        "price_in": "0",
        "price_out": "0",
    }


async def refresh(force: bool = False) -> list[dict]:
    global _rows, _updated_at
    async with _lock:
        if _updated_at and time.time() - _updated_at < REFRESH_SECONDS and not force:
            return [dict(row) for row in _rows]
        async with httpx.AsyncClient(timeout=httpx.Timeout(20, connect=5), follow_redirects=False) as client:
            response = await client.get(CATALOG_URL, headers={"Accept": "application/json", "User-Agent": "Nuxiva"})
            response.raise_for_status()
        payload = response.json()
        entries = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise ValueError("catalog_invalid")
        normalized = [row for row in (normalize_model(item) for item in entries if isinstance(item, dict)) if row]
        normalized.sort(key=lambda row: row["id"])
        _rows, _updated_at = normalized, time.time()
        return [dict(row) for row in _rows]


def cached() -> list[dict]:
    return [dict(row) for row in _rows]


def updated_at() -> float:
    return _updated_at
