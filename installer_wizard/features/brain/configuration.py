"""Canonical provider references for Cervello, including older saved settings."""
from urllib.parse import urlsplit, urlunsplit

from features.cloud.catalog import is_cloud, make_ref, parse_ref

ALIASES = {"google": "gemini", "azure_openai": "azure"}


def provider_id(value: str) -> str:
    return ALIASES.get(value, value)


def selection(body: dict) -> tuple[str, str]:
    method = body.get("provider") or body.get("method") or "ollama_local"
    model = str(body.get("modelName") or body.get("assignedModel") or "").strip()
    if not model or len(model) > 160 or any(c.isspace() for c in model):
        raise ValueError("Modello non valido")
    if method in ("api_key", "cloud"):
        pid = provider_id(str(body.get("providerId") or body.get("serverId") or ""))
        ref = model if is_cloud(model) else make_ref(pid, model)
        parse_ref(ref)
        return ref, ""
    if method not in ("ollama_local", "ollama_remote") or is_cloud(model):
        raise ValueError("Provider non valido")
    raw = "http://127.0.0.1:11434" if method == "ollama_local" else str(body.get("baseUrl") or "").strip()
    if not raw:
        raise ValueError("Indirizzo Ollama remoto mancante")
    parts = urlsplit(raw if "://" in raw else "http://" + raw)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Indirizzo Ollama non valido")
    if parts.query or parts.fragment or parts.path.strip("/") or any(c.isspace() for c in raw):
        raise ValueError("Indirizzo Ollama non valido")
    host = f"[{parts.hostname}]" if ":" in parts.hostname else parts.hostname
    return model, urlunsplit((parts.scheme, f"{host}:{parts.port or 11434}", "", "", ""))


def legacy_ref(model: str, env: dict) -> str:
    if is_cloud(model) or env.get("NUXIVA_BRAIN") != "cloud":
        return model
    pid = provider_id(env.get("NUXIVA_CLOUD_PROVIDER") or "")
    if not pid:
        pid = "gemini" if model.startswith("gemini-") else "anthropic" if model.startswith("claude-") else ""
    if not pid:
        return model
    ref = make_ref(pid, model)
    try:
        parse_ref(ref)
    except ValueError:
        return model
    return ref


def migrate_legacy() -> None:
    from config import read_env, write_env
    from features.brain.roles import ROLES
    env = read_env()
    updates = {}
    for key in ("NUXIVA_LLM_MODEL", "NUXIVA_LLM_FAST_MODEL", *(r.env_key for r in ROLES)):
        old = env.get(key, "")
        new = ",".join(legacy_ref(m.strip(), env) for m in old.split(",") if m.strip())
        if old and new != old:
            updates[key] = new
    if updates:
        write_env(updates)
