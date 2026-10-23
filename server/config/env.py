import secrets
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    NUXIVA_ENV: Literal["development", "production", "testing"] = "development"
    NUXIVA_HOST: str = "0.0.0.0"
    NUXIVA_CORS_ORIGINS: str = ""
    NUXIVA_PORT: int = 8443
    NUXIVA_WEB_PORT: int = 80
    NUXIVA_SECRET_KEY: str = (
        "0000000000000000000000000000000000000000000000000000000000000000"
    )
    DATA_DIR: str = "./data"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_PROVIDER: str = "ollama"
    SYSTEM1_MODEL: str = "qwen2.5:0.5b"
    BABBLING_MODEL: str = "llama3.2"
    SYSTEM2_MODEL: str = "qwen2.5:7b"
    SEMANTIC_CACHE_THRESHOLD: float = 0.90
    SEMANTIC_CACHE_ENABLED: bool = True
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    NUXIVA_LLM_MODEL: str = ""
    NUXIVA_CLAUDE_MODEL: str = "claude-sonnet-5-5"
    NUXIVA_OPENAI_MODEL: str = "gpt-4.1-mini"
    NUXIVA_GEMINI_MODEL: str = "gemini-2.5-flash"
    NUXIVA_LLM_FAST_MODEL: str = ""
    NUXIVA_LLM_CHAT_ORDER: str = ""
    NUXIVA_LLM_DEEP_ORDER: str = ""
    NUXIVA_LLM_RICERCATORE_ORDER: str = ""
    NUXIVA_LLM_DOMOTICO_ORDER: str = ""
    NUXIVA_LLM_STUDIO_ORDER: str = ""
    NUXIVA_LLM_CODER_ORDER: str = ""
    NUXIVA_LLM_3D_ORDER: str = ""
    NUXIVA_EMBED_MODEL: str = "nomic-embed-text"
    NUXIVA_ASSISTANT_NAME: str = ""
    NUXIVA_ASSISTANT_GENDER: str = ""
    NUXIVA_USER_NAME: str = ""
    NUXIVA_DEFAULT_LANGUAGE: str = "it"
    HOME_ASSISTANT_URL: str = "http://127.0.0.1:8123"

    HOME_ASSISTANT_TOKEN: str = ""
    FRIGATE_URL: str = "http://127.0.0.1:5000"
    CODE_SANDBOX_TIMEOUT_SECONDS: int = 30
    SANDBOX_SOCKET_PATH: str = "/run/nuxiva/sandbox/broker.sock"
    SKILL_SANDBOX_MIN_STRENGTH: Literal["container", "userspace_kernel", "microvm"] = "microvm"
    SKILL_SANDBOX_EGRESS_MIN_STRENGTH: Literal["container", "userspace_kernel", "microvm"] = "userspace_kernel"
    SKILL_SYNTHESIS_PER_HOUR: int = 6
    CONSENSUS_CRITICAL_MIN_MODELS: int = 2
    CONSENSUS_CRITICAL_TIMEOUT_SECONDS: float = 45.0
    BRAIN_ROUTES_PATH: str = "/run/nuxiva/brain/routes.json"
    NUXIVA_SUPERVISOR_URL: str = "http://127.0.0.1:8080"
    
    # Proxmox Configuration
    PROXMOX_HOST: str = ""
    PROXMOX_USER: str = ""
    PROXMOX_PASSWORD: str = ""
    PROXMOX_TOKEN_ID: str = ""
    PROXMOX_TOKEN_SECRET: str = ""
    PROXMOX_VERIFY_SSL: bool = False

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = ServerSettings()
if not settings.NUXIVA_SECRET_KEY.strip("0"):
    settings.NUXIVA_SECRET_KEY = secrets.token_hex(32)
