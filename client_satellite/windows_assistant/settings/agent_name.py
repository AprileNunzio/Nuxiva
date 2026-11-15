import re

MAX_LENGTH = 32
FORBIDDEN = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*]')
LEADING = re.compile(r"^(?:hey|hei|ehi|hi|ok|okay)\s+", re.I)
FORBIDDEN_NAMES = {"jarvis"}
DEFAULT = "Nuxiva"


def clean(raw) -> str:
    if not isinstance(raw, str):
        return ""
    text = FORBIDDEN.sub("", raw)
    text = LEADING.sub("", " ".join(text.split())).strip(" .")
    cleaned = text[:MAX_LENGTH].strip(" .")
    return "" if cleaned.casefold() in FORBIDDEN_NAMES else cleaned


def display(name: str) -> str:
    chosen = clean(name)
    if not chosen or chosen.casefold() == DEFAULT.casefold():
        return DEFAULT
    return f"{DEFAULT} · {chosen}"


def shortcut_file(name: str) -> str:
    chosen = clean(name)
    return f"{chosen}.lnk" if chosen and chosen.casefold() != DEFAULT.casefold() else ""
