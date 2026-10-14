import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from features.locale.colocated.errors import BundleCorrupted, LocaleRejected, ScopeRejected

LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
SCOPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:/[a-z0-9][a-z0-9_-]*){1,6}$")
KEY_PATTERN = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+){0,7}$")
TOKEN_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]{1,64})\s*\}\}")
RTL_LANGUAGES = frozenset({"ar", "he", "fa", "ur"})
MAX_LOCALE_LENGTH = 6
MAX_SCOPE_LENGTH = 160
MAX_KEY_LENGTH = 128
MAX_VALUE_LENGTH = 4000
MAX_ENTRIES = 2000


@dataclass(frozen=True)
class Locale:
    code: str

    @classmethod
    def parse(cls, raw: object, allowed: frozenset[str]) -> "Locale":
        clean = raw.strip() if isinstance(raw, str) else ""
        if len(clean) > MAX_LOCALE_LENGTH or not LOCALE_PATTERN.fullmatch(clean):
            raise LocaleRejected("Malformed locale")
        if clean.split("-", 1)[0] not in allowed:
            raise LocaleRejected("Unsupported locale")
        return cls(clean)

    @property
    def language(self) -> str:
        return self.code.split("-", 1)[0]

    @property
    def direction(self) -> str:
        return "rtl" if self.language in RTL_LANGUAGES else "ltr"


@dataclass(frozen=True)
class Scope:
    path: str

    @classmethod
    def parse(cls, raw: object) -> "Scope":
        if not isinstance(raw, str):
            raise ScopeRejected("Scope must be string")
        clean = raw.strip()
        if clean.startswith("/") or clean.endswith("/") or len(clean) > MAX_SCOPE_LENGTH or not SCOPE_PATTERN.fullmatch(clean):
            raise ScopeRejected("Malformed scope")
        return cls(clean)

    @property
    def root(self) -> str:
        return self.path.split("/", 1)[0]

    @property
    def relative(self) -> str:
        return self.path.split("/", 1)[1]


@dataclass(frozen=True)
class TranslationBundle:
    scope: Scope
    locale: Locale
    sources: tuple[str, ...]
    dictionary: Mapping[str, str]
    fallback_keys: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "meta": {
                "scope": self.scope.path,
                "locale": self.locale.code,
                "direction": self.locale.direction,
                "sources": list(self.sources),
                "fallback_keys": list(self.fallback_keys),
            },
            "dictionary": dict(self.dictionary),
        }


def tokens_of(value: str) -> frozenset[str]:
    return frozenset(TOKEN_PATTERN.findall(value))


def parse_dictionary(raw: object, origin: str) -> Mapping[str, str]:
    if not isinstance(raw, dict):
        raise BundleCorrupted(f"{origin}: dictionary must be an object")
    if len(raw) > MAX_ENTRIES:
        raise BundleCorrupted(f"{origin}: dictionary exceeds {MAX_ENTRIES} entries")
    clean: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or len(key) > MAX_KEY_LENGTH or not KEY_PATTERN.fullmatch(key):
            raise BundleCorrupted(f"{origin}: invalid key")
        if not isinstance(value, str) or not value.strip() or len(value) > MAX_VALUE_LENGTH:
            raise BundleCorrupted(f"{origin}: invalid value for {key}")
        clean[key] = value
    return MappingProxyType(clean)


def parse_meta(raw: object, locale_code: str, origin: str) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        raise BundleCorrupted(f"{origin}: meta must be an object")
    declared = raw.get("locale")
    if declared is not None and declared != locale_code:
        raise BundleCorrupted(f"{origin}: meta.locale does not match file name")
