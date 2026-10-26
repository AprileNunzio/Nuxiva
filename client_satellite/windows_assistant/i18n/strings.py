import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger("nuxiva.i18n")
DIR = Path(__file__).resolve().parent
FALLBACK = "en"
WINDOWS_LANGUAGES = {0x10: "it", 0x0C: "fr", 0x09: "en"}


def detect() -> str:
    forced = os.environ.get("NUXIVA_LANG", "").strip().lower()
    if forced:
        return forced[:2]
    if sys.platform == "win32":
        import ctypes
        return WINDOWS_LANGUAGES.get(ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF, FALLBACK)
    return (os.environ.get("LANG", FALLBACK)[:2] or FALLBACK).lower()


def _load(language: str) -> dict:
    path = DIR / f"{language}.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.error("Dizionario %s illeggibile: %s", language, exc)
        return {}
    return data if isinstance(data, dict) else {}


class Translator:
    def __init__(self, language: str | None = None) -> None:
        self.language = language or detect()
        self.table = _load(self.language)
        self.fallback = _load(FALLBACK)

    def __call__(self, key: str, **values) -> str:
        template = self.table.get(key) or self.fallback.get(key) or key
        try:
            return template.format(**values)
        except (KeyError, IndexError):
            log.error("Segnaposto mancanti nella chiave %s", key)
            return template


t = Translator()
