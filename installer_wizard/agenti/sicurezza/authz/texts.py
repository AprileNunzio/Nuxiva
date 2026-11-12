import json
import logging
from functools import lru_cache
from pathlib import Path

FOLDER = Path(__file__).with_name("language")
FALLBACK = "it"
log = logging.getLogger("nuxiva.authz.texts")


@lru_cache(maxsize=8)
def _dictionary(lang: str) -> dict[str, str]:
    try:
        data = json.loads((FOLDER / f"{lang}.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        log.error("Testi di autorizzazione illeggibili per %s: %s", lang, exc)
        return {}
    words = data.get("dictionary") if isinstance(data, dict) else None
    return {k: v for k, v in (words or {}).items() if isinstance(k, str) and isinstance(v, str)}


def language() -> str:
    from agenti.locale.service import system_reply
    return system_reply()


def say(key: str, lang: str | None = None) -> str:
    chosen = lang or language()
    return _dictionary(chosen).get(key) or _dictionary(FALLBACK).get(key) or key
