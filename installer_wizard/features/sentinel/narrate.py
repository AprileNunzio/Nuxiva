import json
import string
from functools import lru_cache
from pathlib import Path

LANGS = ("it", "en", "fr", "es")
FOLDER = Path(__file__).resolve().parent / "language"


@lru_cache(maxsize=None)
def table(lang: str) -> dict:
    path = FOLDER / f"{lang if lang in LANGS else 'it'}.json"
    return json.loads(path.read_text(encoding="utf-8")).get("narrative") or {}


class _Safe(dict):
    def __missing__(self, key):
        return ""


def word(value: str, lang: str) -> str:
    if value.startswith("sentinel."):
        return table(lang).get(value) or table("it").get(value) or ""
    return value


def text(event: dict, lang: str = "it") -> str:
    narrative = event.get("narrative") or {}
    template = table(lang).get(narrative.get("key")) or table("it").get(narrative.get("key")) or ""
    params = {k: word(str(v), lang) for k, v in (narrative.get("params") or {}).items()}
    fields = {name for _, name, _, _ in string.Formatter().parse(template) if name}
    return template.format_map(_Safe({k: v for k, v in params.items() if k in fields}))
