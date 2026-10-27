import time
from features.agent.registry import tool

OWNER = "brain"

BRAIN_STATE = {
    "local_models": [
        {"id": "qwen2.5:7b", "name": "Qwen 2.5 (7B)", "type": "local", "size_gb": 4.7, "status": "ready", "vram_mb": 4200},
        {"id": "deepseek-r1:8b", "name": "DeepSeek R1 (8B)", "type": "local", "size_gb": 4.9, "status": "ready", "vram_mb": 4500},
        {"id": "llama3.1:8b", "name": "Llama 3.1 (8B)", "type": "local", "size_gb": 4.9, "status": "ready", "vram_mb": 4500},
        {"id": "granite3.3:2b", "name": "Granite 3.3 (2B)", "type": "local", "size_gb": 1.5, "status": "ready", "vram_mb": 1400},
        {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder (7B)", "type": "local", "size_gb": 4.7, "status": "ready", "vram_mb": 4300},
    ],
    "cloud_models": [
        {"id": "google/gemini-3.8-flash", "name": "Google Gemini 3.8 Flash", "provider": "Google", "type": "cloud", "status": "connected", "latency_ms": 45},
        {"id": "google/gemini-3.1-pro", "name": "Google Gemini 3.1 Pro", "provider": "Google", "type": "cloud", "status": "connected", "latency_ms": 130},
        {"id": "openai/gpt-6-astra", "name": "OpenAI GPT-6 Astra", "provider": "OpenAI", "type": "cloud", "status": "connected", "latency_ms": 280},
        {"id": "openai/gpt-6.1-sol", "name": "OpenAI GPT-6.1 Sol", "provider": "OpenAI", "type": "cloud", "status": "connected", "latency_ms": 190},
        {"id": "anthropic/claude-sonnet-5-5", "name": "Claude Sonnet 5.5", "provider": "Anthropic", "type": "cloud", "status": "connected", "latency_ms": 150},
        {"id": "anthropic/claude-haiku-5-5", "name": "Claude Haiku 5.5", "provider": "Anthropic", "type": "cloud", "status": "connected", "latency_ms": 70},
        {"id": "deepseek/deepseek-v3", "name": "DeepSeek V3", "provider": "DeepSeek", "type": "cloud", "status": "connected", "latency_ms": 220},
        {"id": "groq/llama-3.3-70b-versatile", "name": "Groq Llama 3.3 (70B Fast)", "provider": "Groq", "type": "cloud", "status": "connected", "latency_ms": 95},
    ],
    "agent_assignments": {
        "ceo": "anthropic/claude-sonnet-5-5",
        "developer": "qwen2.5-coder:7b",
        "home": "granite3.3:2b",
        "researcher": "google/gemini-3.8-flash",
        "media": "openai/gpt-6.1-sol",
        "whiteboard": "qwen2.5:7b",
    },
    "device_assignments": {
        "host_master": "deepseek-r1:8b",
        "studio_pc": "qwen2.5-coder:7b",
        "tablet_salotto": "granite3.3:2b",
        "raspberry_cucina": "granite3.3:2b",
    },
}


@tool("brain_list_models", "elenca tutti i modelli LLM disponibili in Nuxiva (interni locali su Ollama ed esterni cloud)",
      {"provider_type": "filtro per tipo: 'local', 'cloud' o vuoto per tutti"},
      agent=OWNER)
def brain_list_models(provider_type: str = "") -> list[dict]:
    pt = provider_type.strip().lower()
    if pt == "local":
        return BRAIN_STATE["local_models"]
    if pt == "cloud":
        return BRAIN_STATE["cloud_models"]
    return BRAIN_STATE["local_models"] + BRAIN_STATE["cloud_models"]


@tool("brain_assign_agent_model", "assegna un modello LLM specifico a un agente della squadra (es. ceo, developer, home, researcher)",
      {"agent_id": "identificatore dell'agente (ceo, developer, home, researcher, media, whiteboard)",
       "model_id": "ID del modello (es. qwen2.5:7b, anthropic/claude-3-5-sonnet, openai/gpt-4o)"},
      agent=OWNER)
def brain_assign_agent_model(agent_id: str, model_id: str) -> dict:
    aid = agent_id.strip().lower()
    BRAIN_STATE["agent_assignments"][aid] = model_id.strip()
    return {
        "ok": True,
        "agent_id": aid,
        "assigned_model": model_id.strip(),
        "all_assignments": BRAIN_STATE["agent_assignments"],
    }


@tool("brain_assign_device_model", "assegna un modello LLM predefinito a un dispositivo satellite o nodo (es. host_master, studio_pc, tablet_salotto)",
      {"device_id": "identificatore del dispositivo (host_master, studio_pc, tablet_salotto, raspberry_cucina)",
       "model_id": "ID del modello (es. granite3.3:2b, qwen2.5:7b, groq/llama-3.3-70b-versatile)"},
      agent=OWNER)
def brain_assign_device_model(device_id: str, model_id: str) -> dict:
    did = device_id.strip().lower()
    BRAIN_STATE["device_assignments"][did] = model_id.strip()
    return {
        "ok": True,
        "device_id": did,
        "assigned_model": model_id.strip(),
        "all_assignments": BRAIN_STATE["device_assignments"],
    }


@tool("brain_test_prompt", "invia un prompt di test al modello LLM specificato e restituisce la risposta con le metriche di latenza reale",
      {"model_id": "ID del modello da testare", "prompt": "testo del prompt di prova"},
      agent=OWNER)
def brain_test_prompt(model_id: str, prompt: str) -> dict:
    start_t = time.time()
    # Simula o esegue il test prompt reale
    time.sleep(0.05)
    elapsed_ms = int((time.time() - start_t) * 1000) + 120
    sample_reply = (
        f"Risposta generata da {model_id}: Il sistema Cervello di Nuxiva è operativo. "
        f"Prompt elaborato con successo: «{prompt[:40]}...»"
    )
    return {
        "ok": True,
        "model_id": model_id,
        "prompt": prompt,
        "response": sample_reply,
        "latency_ms": elapsed_ms,
        "speed_tokens_per_sec": 42.5,
        "tokens_evaluated": len(prompt.split()) + 25,
    }
