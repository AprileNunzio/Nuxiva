import json
import os
from functools import lru_cache
from pathlib import Path

LANGUAGES = ("it", "en", "es", "fr")


@lru_cache(maxsize=4)
def messages(language: str) -> dict:
    if language not in LANGUAGES:
        language = "en"
    raw = json.loads((Path(__file__).parent / "language" / f"{language}.json").read_text(encoding="utf-8"))
    return raw.get("messages", {})


def translate(key: str, language: str | None = None, **values: str) -> str:
    language = (language or os.environ.get("NUXIVA_UI_LANG", "it")).split("-")[0]
    template = messages(language).get(key) or messages("en").get(key) or key
    return template.format(**values)
