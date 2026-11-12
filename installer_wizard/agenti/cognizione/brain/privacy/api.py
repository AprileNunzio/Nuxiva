from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from state import store

from agenti.brain.privacy import origin as origins
from agenti.brain.privacy.gate import privacy_gate
from agenti.brain.privacy.policy import CHOICES, PROFILES, SLUG, PolicyError

admin_routes = APIRouter()
MAX_BODY = 512


def _people() -> list[dict]:
    from agenti.people import people
    out = []
    for p in people.all_profiles(light=True):
        slug = str(p.get("slug") or "")
        if not SLUG.match(slug):
            continue
        name = " ".join(x for x in (p.get("first_name"), p.get("last_name")) if x) or p.get("name") or slug
        own = privacy_gate.policies.own(slug)
        out.append({"slug": slug, "name": str(name)[:120], "role": str(p.get("role") or ""),
                    "policy": own.to_json() if own else None})
    return out


def _overview() -> dict:
    from agenti.brain.residency import primary
    gate = privacy_gate.policies
    return {
        "default": gate.default().to_json(),
        "automatic": gate.default_is_automatic(),
        "suggested": gate.automatic().to_json(),
        "profiles": {k: dict(v) for k, v in PROFILES.items()},
        "choices": list(CHOICES),
        "engine": {"origin": origins.engine(), "model": primary() or ""},
        "people": _people(),
        "audit": privacy_gate.audit.summary(),
    }


async def _body(request: Request) -> dict:
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "privacy_invalid")
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(400, "privacy_invalid") from exc
    if not isinstance(body, dict):
        raise HTTPException(400, "privacy_invalid")
    return body


@admin_routes.get("/api/brains/privacy")
async def privacy_overview(_: str = Depends(require_admin)):
    return _overview()


@admin_routes.put("/api/brains/privacy/default")
async def privacy_default(request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    try:
        chosen = privacy_gate.policies.set_default(body)
    except PolicyError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.event("INFO", f"Privacy del Cervello: profilo predefinito {chosen.profile} impostato da {user}", "models")
    return _overview()


@admin_routes.put("/api/brains/privacy/people/{slug}")
async def privacy_person(slug: str, request: Request, user: str = Depends(require_admin)):
    if not SLUG.match(slug) or slug not in {p["slug"] for p in _people()}:
        raise HTTPException(404, "privacy_unknown_person")
    body = await _body(request)
    try:
        chosen = privacy_gate.policies.set_person(slug, body)
    except PolicyError as exc:
        raise HTTPException(400, str(exc)) from exc
    label = chosen.profile if chosen else "predefinito"
    store.event("INFO", f"Privacy del Cervello: profilo {label} per {slug} impostato da {user}", "models")
    return _overview()
