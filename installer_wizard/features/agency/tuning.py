from config import env_get

from features.agency.client import client

HARD_CAP = 64
DEFAULT_MAX = 16
DEFAULT_RESERVE_MB = 2048
DEFAULT_RPM = 30
DEFAULT_SIZE_MB = 4700
MAX_RESERVE_MB = 1 << 20


def _bounded(raw: str, default: int, low: int, high: int) -> int:
    try:
        value = int(str(raw).strip())
    except ValueError:
        return default
    return value if low <= value <= high else default


def scheduler() -> dict:
    parallel = env_get("NUXIVA_AGENCY_PARALLEL", "auto").strip().lower()
    manual = parallel != "auto"
    return {
        "mode": "manual" if manual else "auto",
        "manual_parallel": _bounded(parallel, 2, 1, HARD_CAP) if manual else 2,
        "max_parallel": _bounded(env_get("NUXIVA_AGENCY_MAX_PARALLEL", str(DEFAULT_MAX)), DEFAULT_MAX, 1, HARD_CAP),
        "reserve_ram_mb": _bounded(env_get("NUXIVA_AGENCY_RESERVE_MB", str(DEFAULT_RESERVE_MB)), DEFAULT_RESERVE_MB, 0, MAX_RESERVE_MB),
    }


async def model() -> dict:
    from features.brain import llm
    from features.brain.brains import _BY_NAME
    from features.cloud.catalog import is_cloud
    chain = await llm.component_chain("agency_worker") or await llm.chain("deep")
    first = chain[0] if chain else ""
    if first and is_cloud(first):
        rpm = _bounded(env_get("NUXIVA_AGENCY_CLOUD_RPM", str(DEFAULT_RPM)), DEFAULT_RPM, 1, 10000)
        return {"kind": "cloud", "requests_per_minute": rpm}
    name = first if ":" in first else f"{first}:latest"
    entry = _BY_NAME.get(first) or _BY_NAME.get(name) or {}
    size = entry.get("size_gb")
    return {"kind": "local", "size_mb": int(size * 1024) if isinstance(size, (int, float)) and size > 0 else DEFAULT_SIZE_MB}


class Tuner:
    def __init__(self) -> None:
        self.applied: dict | None = None

    async def sync(self) -> bool:
        wanted = {"scheduler": scheduler(), "model": await model()}
        if wanted == self.applied:
            return False
        await client.call("settings_set", **wanted)
        self.applied = wanted
        return True


tuner = Tuner()
