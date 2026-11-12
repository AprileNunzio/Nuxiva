import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from .hardware import calculate_hardware_profile
from .types import OllamaRuntimeConfig

CONFIG_PATH = Path("/etc/nuxiva/ollama_config.json")
SYSTEMD_OVERRIDE_DIR = Path("/etc/systemd/system/ollama.service.d")
SYSTEMD_OVERRIDE_FILE = SYSTEMD_OVERRIDE_DIR / "nuxiva.conf"


def get_default_config() -> OllamaRuntimeConfig:
    profile = calculate_hardware_profile()
    return OllamaRuntimeConfig(
        num_parallel=profile.recommended_parallel,
        num_ctx=profile.recommended_context,
        num_predict=profile.recommended_max_tokens,
        max_loaded_models=profile.recommended_loaded_models,
        flash_attention=profile.recommended_flash_attention,
        keep_alive="24h",
        cpu_weight=100,
        nice=0,
        num_thread=profile.recommended_threads,
        max_queue=512,
        mode="auto",
    )


def load_config() -> OllamaRuntimeConfig:
    if CONFIG_PATH.is_file():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return OllamaRuntimeConfig.from_dict(data)
        except (OSError, ValueError):
            pass
    return get_default_config()


def save_config(config: OllamaRuntimeConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)


def generate_systemd_override(config: OllamaRuntimeConfig) -> str:
    lines = [
        "# Gestito da Nuxiva OS (Auto-Tuning Hardware)",
        "[Service]",
        'Environment="OLLAMA_HOST=127.0.0.1:11434"',
        f'Environment="OLLAMA_KEEP_ALIVE={config.keep_alive}"',
        f'Environment="OLLAMA_MAX_LOADED_MODELS={config.max_loaded_models}"',
        f'Environment="OLLAMA_NUM_PARALLEL={config.num_parallel}"',
        f'Environment="OLLAMA_MAX_QUEUE={config.max_queue}"',
    ]
    if config.flash_attention:
        lines.append('Environment="OLLAMA_FLASH_ATTENTION=1"')
    lines.extend([
        "Restart=always",
        "RestartSec=3",
        f"CPUWeight={config.cpu_weight}",
        f"Nice={config.nice}",
    ])
    return "\n".join(lines) + "\n"


def apply_systemd_configuration(config: OllamaRuntimeConfig) -> bool:
    if not shutil.which("systemctl"):
        return True
    try:
        SYSTEMD_OVERRIDE_DIR.mkdir(parents=True, exist_ok=True)
        content = generate_systemd_override(config)
        with open(SYSTEMD_OVERRIDE_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        subprocess.run(["systemctl", "daemon-reload"], check=True, timeout=10)
        subprocess.run(["systemctl", "restart", "ollama"], check=True, timeout=15)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def get_runtime_options(kind: str = "deep", component: str = "") -> Dict[str, Any]:
    config = load_config()
    ctx = config.num_ctx
    predict = config.num_predict
    if kind == "fast" and not component:
        ctx = min(ctx, 4096)
        predict = min(predict, 1024)
    return {
        "num_ctx": ctx,
        "num_predict": predict,
        "num_thread": config.num_thread,
    }
