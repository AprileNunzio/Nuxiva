from features.agent.registry import tool
from features.cloud.catalog import BY_ID, PROVIDERS
from features.cloud.vault import vault


@tool("cloud_catalog", "elenca i fornitori cloud LLM, i modelli di ultima generazione disponibili e lo stato di configurazione",
      {"provider": "identificativo opzionale del fornitore per filtrare (es. gemini, openai, anthropic)"})
async def cloud_catalog(provider: str = "") -> dict:
    pid = provider.strip().lower()
    specs = [BY_ID[pid]] if pid in BY_ID else PROVIDERS
    return {
        "providers": [
            {
                "id": p.id,
                "name": p.name,
                "kind": p.kind,
                "configured": vault.configured(p.id),
                "models": list(p.models),
                "reasoning": p.reasoning,
                "notes": p.notes,
            }
            for p in specs
        ]
    }
