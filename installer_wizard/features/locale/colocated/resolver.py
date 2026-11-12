from types import MappingProxyType
from typing import Mapping, Optional

from features.locale.colocated.domain import Locale, Scope, TranslationBundle
from features.locale.colocated.errors import BundleNotFound
from features.locale.colocated.repository import LanguageFileRepository
from features.locale.colocated.roots import ScopeRoots


class BundleResolver:
    def __init__(self, roots: ScopeRoots, repository: LanguageFileRepository, fallbacks: tuple[str, ...]) -> None:
        self._roots = roots
        self._repository = repository
        self._fallbacks = fallbacks

    def resolve(self, scope: Scope, locale: Locale) -> TranslationBundle:
        layers = [(code, found) for code in self._chain(locale) if (found := self._layer(scope, code)) is not None]
        if not layers:
            raise BundleNotFound(f"No dictionary for {scope.path}")
        merged: dict[str, str] = {}
        for _, dictionary in reversed(layers):
            merged.update(dictionary)
        primary = layers[0][1] if layers[0][0] in (locale.code, locale.language) else {}
        missing = tuple(sorted(key for key in merged if key not in primary))
        return TranslationBundle(
            scope=scope,
            locale=locale,
            sources=tuple(code for code, _ in layers),
            dictionary=MappingProxyType(merged),
            fallback_keys=missing,
        )

    def _chain(self, locale: Locale) -> tuple[str, ...]:
        return tuple(dict.fromkeys((locale.code, locale.language, *self._fallbacks)))

    def _layer(self, scope: Scope, code: str) -> Optional[Mapping[str, str]]:
        for path in self._roots.candidates(scope, code):
            found = self._repository.dictionary(path)
            if found is not None:
                return found
        return None
