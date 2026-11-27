import httpx


def norm_model(model: str) -> str:
    return model if ":" in model else f"{model}:latest"


def resident_first() -> bool:
    from agenti.brain.brains import brains
    from agenti.cloud.catalog import is_cloud
    chat = brains.config().get("chat") or []
    return bool(chat) and not is_cloud(chat[0])


def judge(model: str, loaded: list[str], installed: list[str], resident: bool) -> dict:
    if model in loaded:
        return {"status": "ok", "detail": f"{model} attivo in memoria"}
    if model not in installed:
        return {"status": "warn", "detail": f"{model} non installato in Ollama"}
    if resident:
        return {"status": "warn", "detail": f"{model} installato ma non caricato in memoria"}
    return {"status": "ok", "detail": f"{model} installato, si carica alla prima richiesta", "on_demand": True}


async def probe(client: httpx.AsyncClient, base: str, model: str) -> dict:
    try:
        ps = await client.get(f"{base}/api/ps")
        ps.raise_for_status()
        tags = await client.get(f"{base}/api/tags")
        tags.raise_for_status()
        loaded = [m.get("name") for m in ps.json().get("models", []) if isinstance(m, dict)]
        installed = [m.get("name") for m in tags.json().get("models", []) if isinstance(m, dict)]
    except (httpx.HTTPError, ValueError, AttributeError):
        return {"status": "down", "detail": f"{model} · Ollama non risponde"}
    return judge(model, loaded, installed, resident_first())
