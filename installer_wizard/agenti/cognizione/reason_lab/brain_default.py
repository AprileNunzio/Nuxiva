from fastapi import HTTPException

from agenti.brain.brains import brains
from agenti.cloud.catalog import BY_ID, is_cloud, parse_ref
from agenti.cloud.vault import vault
from config import ollama_url

ROLES = ("main", "fast")


def resolve(role: str = "main") -> dict:
    if role not in ROLES:
        raise HTTPException(422, "brain_role_invalid")
    ref = brains.config()[role]
    if not is_cloud(ref):
        return {"role": role, "ref": ref, "backend": "ollama", "base_url": ollama_url().rstrip("/"), "model": ref, "key": None,
                "provider": "ollama", "supported": True}
    try:
        provider_id, model = parse_ref(ref)
    except ValueError as exc:
        raise HTTPException(422, "brain_reference_invalid") from exc
    spec, entry = BY_ID[provider_id], vault.get(provider_id)
    key = entry.get("key") or None
    base = (entry.get("base_url") or spec.base_url or "").rstrip("/")
    flavor = entry.get("flavor")
    backend = "ollama" if flavor == "ollama" else "openai" if flavor == "openai" or spec.kind == "openai" else None
    if backend == "ollama":
        base = (entry.get("root") or base).rstrip("/")
    supported = backend is not None and bool(base) and vault.configured(provider_id)
    return {"role": role, "ref": ref, "backend": backend or "openai", "base_url": base, "model": model, "key": key,
            "provider": spec.name, "supported": supported}


def public(role: str = "main") -> dict:
    resolved = resolve(role)
    return {key: value for key, value in resolved.items() if key != "key"} | {"has_key": bool(resolved["key"])}
