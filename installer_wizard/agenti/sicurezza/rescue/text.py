import json
import re
from functools import lru_cache
from pathlib import Path

from config import env_get

LANGUAGES = ("it", "en", "fr", "es")
NUMBER = re.compile(r"^[0-9]{2,6}$")


@lru_cache(maxsize=4)
def messages(language: str) -> dict:
    if language not in LANGUAGES:
        language = "en"
    raw = json.loads((Path(__file__).parent / "language" / f"{language}.json").read_text(encoding="utf-8"))
    found = raw.get("messages", {})
    return found if isinstance(found, dict) else {}


def language_of(value: str | None) -> str:
    code = str(value or env_get("NUXIVA_UI_LANG", "it") or "it").split("-")[0].lower()
    return code if code in LANGUAGES else "en"


def emergency_number() -> str:
    value = env_get("NUXIVA_EMERGENCY_NUMBER", "112").strip()
    return value if NUMBER.match(value) else "112"


def translate(key: str, language: str | None = None, **values) -> str:
    lang = language_of(language)
    template = messages(lang).get(key) or messages("en").get(key) or key
    return template.format(number=emergency_number(), **values)
