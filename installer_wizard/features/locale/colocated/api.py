import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from fastapi import APIRouter, Query, Request, Response

from config import FEATURES_DIR, SKILLS_DIR, STATE_DIR, UI_LANGUAGES, WEB_DIR, WIDGETS_DIR
from features.locale.colocated.domain import MAX_LOCALE_LENGTH, MAX_SCOPE_LENGTH, Locale, Scope
from features.locale.colocated.repository import LanguageFileRepository
from features.locale.colocated.resolver import BundleResolver
from features.locale.colocated.roots import ScopeRoots

ROUTE = "/api/i18n/bundle"
FALLBACK_LOCALES = ("en", "it")
ALLOWED_LANGUAGES = frozenset(UI_LANGUAGES)

class _LiveRoots(Mapping):
    def __init__(self, static: dict[str, tuple[Path, ...]]) -> None:
        self._static = static

    def _agent_bases(self) -> tuple[Path, ...]:
        from agenti._registry import registry
        bases = registry.bases()
        return tuple(bases) if bases else (FEATURES_DIR, STATE_DIR / "features")

    def __getitem__(self, key: str) -> tuple[Path, ...]:
        if key == "features":
            return self._agent_bases()
        return self._static[key]

    def __iter__(self):
        return iter(("features", *self._static))

    def __len__(self) -> int:
        return len(self._static) + 1


roots = ScopeRoots(_LiveRoots({
    "web": (WEB_DIR,),
    "skills": (SKILLS_DIR,),
    "widgets": (WIDGETS_DIR,),
}))
resolver = BundleResolver(roots, LanguageFileRepository(), FALLBACK_LOCALES)


def _entity_tag(body: bytes) -> str:
    return f'"{hashlib.sha256(body).hexdigest()[:32]}"'


def _matches(header: str, tag: str) -> bool:
    return any(candidate.strip().removeprefix("W/") == tag for candidate in header.split(","))


async def bundle(
    request: Request,
    scope: str = Query(..., min_length=3, max_length=MAX_SCOPE_LENGTH),
    locale: str = Query(..., min_length=2, max_length=MAX_LOCALE_LENGTH),
) -> Response:
    result = resolver.resolve(Scope.parse(scope), Locale.parse(locale, ALLOWED_LANGUAGES))
    body = json.dumps(result.to_payload(), ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    tag = _entity_tag(body)
    headers = {"ETag": tag, "Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"}
    if _matches(request.headers.get("if-none-match", ""), tag):
        return Response(status_code=304, headers=headers)
    return Response(body, media_type="application/json", headers=headers)


public_routes = APIRouter()
admin_routes = APIRouter()
for _router in (public_routes, admin_routes):
    _router.add_api_route(ROUTE, bundle, methods=["GET"], include_in_schema=False)
