import re
from config import UI_LANGUAGES

PROFILES = {
    "auto": {"label": "Automatico", "model": "", "size_gb": 0.0,
             "note": "Nuxiva sceglie da sola in base all'hardware."},
    "leggero": {"label": "Leggero", "model": "granite3.3:2b", "size_gb": 1.9, "min_ram_gb": 6,
                "note": "Per mini PC e computer con poca memoria."},
    "bilanciato": {"label": "Bilanciato", "model": "granite3.3:8b", "size_gb": 4.9, "min_ram_gb": 14,
                   "note": "Ragionamento migliore, serve un computer recente."},
    "potente": {"label": "Potente", "model": "qwen2.5:14b", "size_gb": 9.0, "min_ram_gb": 28,
                "note": "Massima qualità, consigliato con scheda video da 12 GB o più."},
}

VOICE_CHOICES = {
    "if_sara": "Sara — femminile, naturale (IT)",
    "it_IT-serena-high": "Serena — femminile, alta qualità (IT)",
    "it_IT-paola-medium": "Paola — femminile, veloce (IT)",
    "im_nicola": "Nicola — maschile, naturale (IT)",
    "af_heart": "Heart — female, natural (EN)",
    "am_michael": "Michael — male, natural (EN)",
    "ef_dora": "Dora — femenina, natural (ES)",
    "em_alex": "Alex — masculino, natural (ES)",
    "ff_siwis": "Siwis — féminine, naturelle (FR)",
    "fr_FR-gilles-low": "Gilles — masculin, rapide (FR)",
}

VOICES_BY_LANG_GENDER = {
    "it": {"female": "if_sara", "male": "im_nicola"},
    "en": {"female": "af_heart", "male": "am_michael"},
    "es": {"female": "ef_dora", "male": "em_alex"},
    "fr": {"female": "ff_siwis", "male": "fr_FR-gilles-low"},
}

GREETING_TEMPLATES = {
    "it": "Ciao! Sono {name}. Sono a tua disposizione.",
    "en": "Hello! I am {name}. Ready to assist you.",
    "es": "¡Hola! Soy {name}. A tu servicio.",
    "fr": "Bonjour ! Je suis {name}. Prêt à vous assister.",
}

LANGS = UI_LANGUAGES

NAME_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ-]{0,39}")
HA_URL_RE = re.compile(r"https?://[A-Za-z0-9.-]{1,253}(:\d{1,5})?(/[A-Za-z0-9._~/-]{0,200})?")
HA_TOKEN_RE = re.compile(r"[A-Za-z0-9._-]{20,512}")
TELEGRAM_RE = re.compile(r"\d{5,12}:[A-Za-z0-9_-]{30,64}")
ANSWER_KEYS = {"NUXIVA_USER_NAME", "NUXIVA_UI_LANG", "NUXIVA_VOICE", "NUXIVA_LLM_MODEL", "NUXIVA_COMMERCIAL",
               "HOME_ASSISTANT_URL", "HOME_ASSISTANT_TOKEN", "NUXIVA_TELEGRAM_TOKEN", "NUXIVA_SMB_PASSWORD",
               "NUXIVA_BRAIN", "NUXIVA_OLLAMA_URL", "NUXIVA_CLOUD_PROVIDER", "NUXIVA_CLOUD_KEY", "NUXIVA_PACKAGES"}
BRAINS = ("local", "remote", "cloud")
CLOUD_PICK = {
    "anthropic": ("Anthropic Claude", "claude-haiku-4-5-20251001", "claude-sonnet-5-5"),
    "gemini": ("Google Gemini", "gemini-2.5-flash", "gemini-2.5-pro"),
    "openai": ("OpenAI", "gpt-5-mini", "gpt-5"),
    "mistral": ("Mistral AI", "mistral-small-latest", "mistral-large-latest"),
}
CLOUD_KEY_RE = re.compile(r"[A-Za-z0-9_\-.]{20,256}")
WIZARD_PACKAGES = {"voice": "NUXIVA_VOICE_PACKAGE", "ear": "NUXIVA_EAR", "vision": "NUXIVA_VISION", "documents": "NUXIVA_DOCUMENTS"}
SMB_RE = re.compile(r"[A-Za-z0-9_.@%+=:,-]{12,128}")
