import json
import logging
import re
import threading

from config import STATE_DIR, read_env
from sealed import write_private
from setup_config import CLOUD_PICK, PROFILES, WIZARD_PACKAGES

log = logging.getLogger("nuxiva.setup")
SESSION_FILE = STATE_DIR / "setup_session.json"
STEPS = 7
LOCALES = {"it": "it-IT", "en": "en-US", "es": "es-ES", "fr": "fr-FR"}
SECRET_KEYS = ("ha_token", "cloud_key")
TEXT_RE = re.compile(r"[^\x00-\x1f\x7f<>]*")
ASSISTANT_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{0,31}")
SERVER_KEYS = ("wake_samples", "face_views", "cameras")


def _text(value: object, limit: int) -> str:
    text = " ".join(str(value or "").split())[:limit]
    if not TEXT_RE.fullmatch(text):
        raise ValueError("Testo non valido")
    return text


def _number(value: object, low: float, high: float) -> float:
    number = float(value)
    if not low <= number <= high:
        raise ValueError("Valore fuori intervallo")
    return round(number, 1)


def _mic(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Misura del microfono non valida")
    return {"noise_db": _number(value.get("noise_db"), -140, 0), "voice_db": _number(value.get("voice_db"), -140, 0),
            "snr_db": _number(value.get("snr_db"), -60, 140), "sample_rate": int(_number(value.get("sample_rate"), 8000, 192000)),
            "device": _text(value.get("device"), 120)}


def _choice(options) -> callable:
    def check(value: object) -> str:
        text = str(value or "")
        if text not in options:
            raise ValueError("Scelta non valida")
        return text
    return check


def _assistant(value: object) -> str:
    text = _text(value, 32)
    if text and not ASSISTANT_RE.fullmatch(text):
        raise ValueError("Il nome dell'assistente può contenere solo lettere, spazi, apostrofi e trattini")
    return text


def _packages(value: object) -> list[str]:
    if not isinstance(value, list) or any(p not in WIZARD_PACKAGES for p in value):
        raise ValueError("Pacchetto non valido")
    return list(dict.fromkeys(value))


FIELDS = {
    "locale": _choice(set(LOCALES.values())),
    "assistant_name": _assistant,
    "assistant_gender": _choice({"female", "male"}),
    "owner_name": lambda v: _text(v, 40),
    "owner_last": lambda v: _text(v, 60),
    "mic": _mic,
    "brain": _choice({"local", "remote", "cloud"}),
    "profile": _choice(set(PROFILES)),
    "ollama_url": lambda v: _text(v, 200),
    "cloud_provider": _choice(set(CLOUD_PICK) | {""}),
    "packages": _packages,
    "ha_url": lambda v: _text(v, 260),
    "ha_token": lambda v: _text(v, 512),
    "cloud_key": lambda v: _text(v, 256),
}


def defaults() -> dict:
    env = read_env()
    lang = env.get("NUXIVA_UI_LANG", "it")
    return {"locale": LOCALES.get(lang, "it-IT"), "assistant_name": env.get("NUXIVA_ASSISTANT_NAME", ""),
            "assistant_gender": env.get("NUXIVA_ASSISTANT_GENDER", "female") if env.get("NUXIVA_ASSISTANT_GENDER") in ("male", "female") else "female",
            "owner_name": env.get("NUXIVA_USER_NAME", ""), "owner_last": "", "mic": None, "brain": "local", "profile": "auto",
            "ollama_url": "", "cloud_provider": "", "packages": None, "ha_url": "", "wake_samples": {}, "face_views": [],
            "cameras": None}


class SetupSession:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()
        self._load()

    def reset(self) -> None:
        self.current_step = 1
        self.max_reached_step = 1
        self.completed: set[int] = set()
        self.config = defaults()
        self.secrets: dict[str, str] = {}

    def _load(self) -> None:
        try:
            raw = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            log.warning("Sessione di configurazione illeggibile, ricomincio: %s", exc)
            return
        self.max_reached_step = min(STEPS, max(1, int(raw.get("max_reached_step", 1))))
        self.current_step = min(self.max_reached_step, max(1, int(raw.get("current_step", 1))))
        self.completed = {int(s) for s in raw.get("completed", []) if 1 <= int(s) <= STEPS}
        stored = raw.get("config") or {}
        for key, check in FIELDS.items():
            if key in stored and key not in SECRET_KEYS and stored[key] is not None:
                try:
                    self.config[key] = check(stored[key])
                except (TypeError, ValueError):
                    log.warning("Campo %s della sessione scartato", key)
        for key in SERVER_KEYS:
            if key in stored:
                self.config[key] = stored[key]

    def save(self) -> None:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"current_step": self.current_step, "max_reached_step": self.max_reached_step,
                "completed": sorted(self.completed), "config": self.config}
        write_private(SESSION_FILE, json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def to_dict(self) -> dict:
        return {"current_step": self.current_step, "max_reached_step": self.max_reached_step, "steps": STEPS,
                "completed": sorted(self.completed), "config": dict(self.config),
                "secrets_set": {k: bool(self.secrets.get(k)) for k in SECRET_KEYS}}

    def navigate(self, target: int) -> dict:
        with self._lock:
            if not 1 <= target <= STEPS:
                raise ValueError("Passo inesistente")
            if target > self.max_reached_step:
                raise ValueError("Completa prima i passi precedenti")
            self.current_step = target
            self.save()
            return self.to_dict()

    def update(self, step: int, updates: dict) -> dict:
        with self._lock:
            if not 1 <= step <= STEPS:
                raise ValueError("Passo inesistente")
            clean: dict = {}
            for key, value in updates.items():
                if key not in FIELDS:
                    raise ValueError(f"Campo non ammesso: {str(key)[:40]}")
                clean[key] = FIELDS[key](value)
            for key in SECRET_KEYS:
                if key in clean:
                    secret = clean.pop(key)
                    if secret:
                        self.secrets[key] = secret
                    else:
                        self.secrets.pop(key, None)
            self.config.update(clean)
            self.completed.add(step)
            if step == self.max_reached_step and step < STEPS:
                self.max_reached_step = step + 1
            self.save()
            return self.to_dict()

    def record(self, key: str, value) -> dict:
        with self._lock:
            if key not in SERVER_KEYS:
                raise ValueError("Campo non ammesso")
            self.config[key] = value
            self.save()
            return self.to_dict()

    def clear(self) -> None:
        with self._lock:
            self.reset()
            SESSION_FILE.unlink(missing_ok=True)


session_manager = SetupSession()
