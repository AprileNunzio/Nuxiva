import httpx
from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from state import store

from features.google.flows import flows
from features.google.gservices import google
from features.people import connectors, people

admin_routes = APIRouter()


def _person(slug: str) -> dict:
    profile = people.load(slug)
    if not profile:
        raise HTTPException(404, "Persona non trovata")
    return profile


connectors.register("google", "Google", "mail", google.person_state)


@admin_routes.get("/api/google")
async def admin_google(_: str = Depends(require_admin)):
    return {**google.summary(), "pending": flows.pending()}


@admin_routes.get("/api/google/{slug}/preview")
async def admin_google_preview(slug: str, _: str = Depends(require_admin)):
    _person(slug)
    return await google.preview(slug)


@admin_routes.post("/api/google/{slug}/auth-url")
async def admin_google_url(slug: str, request: Request, _: str = Depends(require_admin)):
    _person(slug)
    body = await request.json() if int(request.headers.get("content-length") or 0) else {}
    try:
        return {"url": google.auth_url(slug, [str(s) for s in body.get("services") or []])}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@admin_routes.post("/api/google/finish")
async def admin_google_finish(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    try:
        slug, email = await google.link(str(body.get("url", ""))[:4000], str(body.get("slug", ""))[:120])
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Google non raggiungibile: {exc}")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Account Google di {slug} collegato da {user}", "google")
    return {**google.summary(), "pending": flows.pending(), "linked": slug, "email": email}


@admin_routes.delete("/api/google/{slug}/pending")
async def admin_google_cancel(slug: str, _: str = Depends(require_admin)):
    flows.cancel(slug)
    return {"pending": flows.pending()}


@admin_routes.post("/api/google/{slug}/services/{service}")
async def admin_google_service_enable(slug: str, service: str, user: str = Depends(require_admin)):
    _person(slug)
    try:
        url = google.enable_service(slug, service)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if url is None:
        store.event("INFO", f"Servizio Google {service} riattivato per {slug} da {user}", "google")
    return {"url": url}


@admin_routes.delete("/api/google/{slug}/services/{service}")
async def admin_google_service_disable(slug: str, service: str, user: str = Depends(require_admin)):
    _person(slug)
    try:
        unlinked = await google.disable_service(slug, service)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Servizio Google {service} disattivato per {slug} da {user}", "google")
    return {"unlinked": unlinked}


@admin_routes.delete("/api/google/{slug}")
async def admin_google_disconnect(slug: str, user: str = Depends(require_admin)):
    _person(slug)
    await google.unlink(slug)
    store.event("INFO", f"Account Google di {slug} scollegato da {user}", "google")
    return google.summary()


@admin_routes.put("/api/google/{slug}/reminder")
async def admin_google_reminder(slug: str, request: Request, user: str = Depends(require_admin)):
    _person(slug)
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Richiesta non valida")
    try:
        minutes = google.set_reminder(slug, body.get("minutes") if isinstance(body, dict) else None)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except LookupError as exc:
        raise HTTPException(409, str(exc))
    store.event("INFO", f"Google: avviso prima degli appuntamenti di {slug} impostato a {minutes} minuti da {user}", "google")
    return {"minutes": minutes}
