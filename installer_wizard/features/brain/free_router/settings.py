import json
import os

from config import STATE_DIR

SETTINGS_FILE = STATE_DIR / "brain" / "free_router.json"
DEFAULTS = {"enabled": False, "pools": ["chat", "agent_tools", "vision", "deep_code", "voice_fast"]}


def load() -> dict:
    if not SETTINGS_FILE.exists():
        return dict(DEFAULTS)
    try:
        value = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("free_router.settings_unavailable") from exc
    if not isinstance(value, dict):
        raise RuntimeError("free_router.settings_invalid")
    pools = value.get("pools")
    from features.brain.free_router.capability_matrix import POOLS
    if not isinstance(pools, list) or any(pool not in POOLS for pool in pools):
        raise RuntimeError("free_router.settings_invalid")
    return {"enabled": value.get("enabled") is True, "pools": list(dict.fromkeys(pools))}


def save(enabled: bool, pools: list[str]) -> dict:
    from features.brain.free_router.capability_matrix import POOLS
    if not isinstance(enabled, bool) or not isinstance(pools, list) or len(pools) > len(POOLS) or any(pool not in POOLS for pool in pools):
        raise ValueError("free_router.settings_invalid")
    data = {"enabled": enabled, "pools": list(dict.fromkeys(pools))}
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(SETTINGS_FILE.parent, 0o750)
    temporary = SETTINGS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, SETTINGS_FILE)
    return data
