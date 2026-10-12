from fastapi import HTTPException

import health
from config import DEMO, _ollama_cache, write_env
from feature_registry import registry
from features.brain.brains import brains
from orchestrator import converge_steps
from state import store
from steps import STEP_BY_ID
from tasks import background

STEP_TRIGGERS = (
    ({"NUXIVA_LLM_MODEL", "NUXIVA_EMBED_MODEL", "NUXIVA_LLM_FAST_MODEL"}, ["preflight", "models", "brain", "warmup"]),
    ({"NUXIVA_LLM_MODEL", "NUXIVA_EMBED_MODEL"}, ["services"]),
    ({"GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN"}, ["services"]),
    ({"NUXIVA_KIOSK"}, ["kiosk"]),
    ({"NUXIVA_VOICE"}, ["voice"]),
    ({"NUXIVA_VISION"}, ["vision"]),
    ({"NUXIVA_EAR", "NUXIVA_STT_MODEL"}, ["ear"]),
    ({"NUXIVA_MUSIC_ID", "NUXIVA_EAR"}, ["music"]),
    ({"NUXIVA_STUDY_FINETUNE"}, ["soup"]),
    ({"NUXIVA_3D_CONVERT"}, ["convert3d"]),
    ({"NUXIVA_COMMERCIAL", "NUXIVA_UNOFFICIAL_SERVICES"}, ["voice", "ear", "music", "models", "brain"]),
    ({"NUXIVA_GPU_DRIVER"}, ["display_driver"]),
    ({"NUXIVA_SHARES", "NUXIVA_SMB_PASSWORD"}, ["shares"]),
    ({"NUXIVA_OLLAMA_URL"}, ["ollama", "models", "brain", "warmup", "services"]),
    ({"NUXIVA_BRAIN"}, ["ollama", "models", "brain", "warmup", "services"]),
    ({"NUXIVA_VOICE_PACKAGE"}, ["voice"]),
    ({"NUXIVA_DOCUMENTS"}, ["office"]),
    ({"NUXIVA_BLUETOOTH"}, ["bluetooth"]),
    ({"NUXIVA_SANDBOX"}, ["sandbox", "gvisor", "firecracker"]),
    ({"NUXIVA_NATIVE"}, ["native"]),
    ({"NUXIVA_ZRAM"}, ["memory"]),
    ({"NUXIVA_CORE_RUNTIME"}, ["docker", "core", "services"]),
)


def normalize_ollama(value: str) -> str:
    url = str(value or "").strip().rstrip("/")
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    if ":" not in url.split("//", 1)[1]:
        url += ":11434"
    if any(c.isspace() for c in url) or url.count("//") != 1:
        raise HTTPException(400, "Indirizzo del server Ollama non valido")
    return url


async def apply_config(updates: dict, user: str, extra_steps: list | None = None) -> list:
    if "NUXIVA_OLLAMA_URL" in updates:
        updates["NUXIVA_OLLAMA_URL"] = normalize_ollama(updates["NUXIVA_OLLAMA_URL"])
    if "NUXIVA_LLM_MODEL" in updates:
        updates["NUXIVA_LLM_MODEL_AUTO"] = "0" if updates["NUXIVA_LLM_MODEL"] else "1"
    if "NUXIVA_LLM_FAST_MODEL" in updates:
        updates["NUXIVA_LLM_FAST_AUTO"] = "0" if updates["NUXIVA_LLM_FAST_MODEL"] else "1"
    try:
        write_env(updates)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    registry.note_env_change(updates)
    if "NUXIVA_OLLAMA_URL" in updates:
        _ollama_cache.clear()
    brains.invalidate()
    store.event("INFO", f"Configurazione aggiornata da {user}: {', '.join(updates)}", "admin")
    needs = list(extra_steps or [])
    for keys, steps in STEP_TRIGGERS:
        if keys & updates.keys():
            needs += steps
    needs = [n for n in dict.fromkeys(needs) if n in STEP_BY_ID]
    if needs:
        if "services" in needs and not DEMO:
            import machine
            if machine.core_runtime() == "native":
                await health.sh("systemctl", "stop", "nuxiva-core", timeout=60)
            else:
                await health.sh("docker", "rm", "-f", "nuxiva-core", timeout=60)
        background(converge_steps(needs, "Applicazione della nuova configurazione"))
    return needs
