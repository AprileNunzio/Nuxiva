import logging
import shutil

from cryptography.fernet import InvalidToken

from config import ollama_remote, read_env

log = logging.getLogger("nuxiva.brain.intent")

UNDECIDED = ("", "pending")


def local_engine() -> bool:
    return shutil.which("ollama") is not None


def _keyed(pid: str) -> bool:
    from features.cloud.catalog import BY_ID, is_server
    from features.cloud.vault import vault
    spec = BY_ID.get(pid)
    if spec is None or is_server(pid) or spec.key_optional:
        return False
    return bool(vault.get(pid).get("key")) and vault.configured(pid)


def _ordered(env: dict) -> list[str]:
    from features.cloud.catalog import PREFIX
    refs = [r.strip() for r in env.get("NUXIVA_LLM_CHAT_ORDER", "").split(",") if r.strip()]
    return [r.removeprefix(PREFIX).partition("/")[0] for r in refs if r.startswith(PREFIX)]


def cloud_provider(env: dict | None = None) -> str:
    from features.cloud.catalog import BY_ID
    env = read_env() if env is None else env
    try:
        return next((pid for pid in [*_ordered(env), *BY_ID] if _keyed(pid)), "")
    except (OSError, ValueError, InvalidToken) as exc:
        log.warning("Chiavi del cervello cloud illeggibili: %s", type(exc).__name__)
        return ""


def cloud_ordered(env: dict) -> bool:
    refs = [r.strip() for r in env.get("NUXIVA_LLM_CHAT_ORDER", "").split(",") if r.strip()]
    return bool(refs) and all(r.startswith("cloud:") for r in refs)


def local_ollama_optional(env: dict | None = None) -> bool:
    env = read_env() if env is None else env
    mode = env.get("NUXIVA_BRAIN", "").strip().lower()
    if mode == "cloud":
        return True
    if mode == "local" or mode == "remote" or ollama_remote():
        return False
    return bool(cloud_provider(env))


def _models(pid: str) -> tuple[str, str]:
    from features.cloud.catalog import BY_ID
    from setup_config import CLOUD_PICK
    if pid in CLOUD_PICK:
        _, fast, deep = CLOUD_PICK[pid]
        return fast, deep
    first = BY_ID[pid].models[0] if BY_ID[pid].models else ""
    return first, first


def reconcile(env: dict | None = None) -> dict:
    env = read_env() if env is None else env
    if env.get("NUXIVA_BRAIN", "").strip().lower() not in UNDECIDED or ollama_remote():
        return {}
    provider = cloud_provider(env)
    if not provider:
        return {}
    updates = {"NUXIVA_BRAIN": "cloud"}
    if not cloud_ordered(env):
        fast, deep = _models(provider)
        if not fast:
            return {}
        updates.update(NUXIVA_LLM_CHAT_ORDER=f"cloud:{provider}/{fast}", NUXIVA_LLM_DEEP_ORDER=f"cloud:{provider}/{deep}")
    return updates
