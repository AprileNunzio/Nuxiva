import json
from functools import lru_cache
from pathlib import Path

LANGUAGES = ("it", "en", "es", "fr")
DIRECTORY = Path(__file__).resolve().parent / "language"


def lang_of(raw: str) -> str:
    base = (raw or "").split("-")[0].split("_")[0].lower()
    return base if base in LANGUAGES else "it"


@lru_cache(maxsize=len(LANGUAGES))
def dictionary(lang: str) -> dict:
    target = DIRECTORY / f"{lang_of(lang)}.json"
    if not target.is_file():
        target = DIRECTORY / "it.json"
    return json.loads(target.read_text(encoding="utf-8"))


def word(lang: str, group: str, key: str) -> str:
    return str(dictionary(lang).get(group, {}).get(key, f"{group}.{key}"))
