from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Tuple

DEFAULT_NAME = "Nuxiva"
MAX_NAME_LENGTH = 32
_WAKE_PREFIX = re.compile(r"^(?:hey|hei|ehi|hi|ok|okay|oye|hé)\s+", re.I)
_DISALLOWED = re.compile(r"[^\w\s'’.-]", re.U)


@dataclass(frozen=True)
class AssistantIdentity:
    name: str
    wake_word: str
    gender: str
    is_custom: bool

    @property
    def wake_phrases(self) -> Tuple[str, ...]:
        return (self.wake_word, f"ehi {self.wake_word}", f"ok {self.wake_word}", f"ciao {self.wake_word}")


def normalize_name(raw: str) -> str:
    text = unicodedata.normalize("NFKC", str(raw or ""))
    text = _DISALLOWED.sub("", _WAKE_PREFIX.sub("", text.strip())).strip()
    text = re.sub(r"\s+", " ", text)[:MAX_NAME_LENGTH].strip()
    if not text:
        return DEFAULT_NAME
    return text.capitalize() if text.isupper() and len(text) > 1 else text


def _env(key: str, default: str) -> str:
    from config import env_get

    return env_get(key, default)


def assistant_identity(reader: Callable[[str, str], str] = _env) -> AssistantIdentity:
    name = normalize_name(reader("NUXIVA_ASSISTANT_NAME", DEFAULT_NAME))
    gender = reader("NUXIVA_ASSISTANT_GENDER", "female").strip().lower()
    return AssistantIdentity(
        name=name,
        wake_word=name.lower(),
        gender=gender if gender in {"female", "male", "neutral"} else "female",
        is_custom=name.lower() != DEFAULT_NAME.lower(),
    )


def assistant_name() -> str:
    return assistant_identity().name
