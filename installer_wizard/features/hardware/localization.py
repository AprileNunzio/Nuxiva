import json
import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def messages(language):
    if language not in ("it", "en", "fr", "es"):
        language = "en"
    return json.loads((Path(__file__).parent / "language" / f"{language}.json").read_text(encoding="utf-8"))["messages"]


def translate(key, language=None, **values):
    language = (language or os.environ.get("NUXIVA_UI_LANG", "it")).split("-")[0]
    return messages(language).get(key, messages("en").get(key, key)).format(**values)
