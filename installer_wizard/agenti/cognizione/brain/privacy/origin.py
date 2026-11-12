from config import ollama_remote, ollama_url

from agenti.brain.privacy.policy import HOME, LOCAL, REMOTE
from agenti.brain.scope import private_url
from agenti.cloud.catalog import BY_ID, is_cloud, is_server, parse_ref


def _by_url(url: str) -> str:
    return HOME if url and private_url(url) else REMOTE


def engine() -> str:
    return _by_url(ollama_url()) if ollama_remote() else LOCAL


def of(ref: str) -> str:
    if not is_cloud(ref):
        return engine()
    try:
        provider, _ = parse_ref(ref)
    except ValueError:
        return REMOTE
    from agenti.cloud.vault import vault
    if is_server(provider):
        entry = vault.servers().get(provider) or {}
        return _by_url(str(entry.get("root") or entry.get("base_url") or ""))
    spec = BY_ID.get(provider)
    base = str(vault.get(provider).get("base_url") or getattr(spec, "base_url", "") or "")
    return _by_url(base)
