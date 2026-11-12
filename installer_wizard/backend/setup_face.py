import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from access import NO_CACHE, is_local
from setup_session import session_manager

router = APIRouter()
FACE_KINDS = ("front", "three_left", "three_right")
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")
MAX_FRAME = 3 * 1024 * 1024
UNAVAILABLE = "Servizio di visione o telecamera del server non disponibile: potrai registrare il volto più tardi dal Gestore Identità"


def require_open(request: Request) -> None:
    import setup_api
    setup_api.require_setup(request)


def _owner() -> tuple[str, str]:
    import setup_owner
    from agenti.people import people
    cfg = session_manager.config
    first, last = setup_owner.clean_names({"name": cfg.get("owner_name"), "last_name": cfg.get("owner_last"),
                                           "assistant_name": cfg.get("assistant_name")})
    name = setup_owner.full_name(first, last)
    slug = people.slugify(name)
    people.ensure(slug, name)
    return slug, name


async def _vision(method: str, path: str, content: bytes | None = None, params: dict | None = None,
                  timeout: float = 10.0) -> httpx.Response:
    from agenti.vision.proxy import VISION_URL
    headers = {"Content-Type": "application/octet-stream"} if content else None
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.request(method, f"{VISION_URL}{path}", params=params, content=content, headers=headers)
    except httpx.HTTPError:
        raise HTTPException(503, UNAVAILABLE)


def _relay(r: httpx.Response) -> Response:
    if r.status_code in (404, 502):
        raise HTTPException(503, UNAVAILABLE)
    return Response(r.content, status_code=r.status_code, media_type=r.headers.get("content-type") or "application/json",
                    headers=NO_CACHE)


async def _frame(request: Request) -> bytes | None:
    ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if not ctype or ctype == "application/json":
        return None
    if ctype not in IMAGE_TYPES:
        raise HTTPException(415, "Invia un fotogramma JPEG, PNG o WEBP")
    try:
        declared = int(request.headers.get("content-length") or 0)
    except ValueError:
        raise HTTPException(400, "Lunghezza non valida")
    if declared > MAX_FRAME:
        raise HTTPException(413, "Fotogramma troppo grande")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_FRAME:
            raise HTTPException(413, "Fotogramma troppo grande")
    if not data:
        raise HTTPException(400, "Fotogramma vuoto")
    return bytes(data)


@router.get("/api/setup/face/context")
async def face_context(request: Request, _: None = Depends(require_open)):
    return JSONResponse({"mode": "server" if is_local(request) else "remote", "kinds": list(FACE_KINDS),
                         "views": list(session_manager.config.get("face_views") or [])}, headers=NO_CACHE)


@router.get("/api/setup/face/preview.jpg")
async def face_preview(_: None = Depends(require_open)):
    r = await _vision("GET", "/frame.jpg", timeout=5)
    if r.status_code != 200 or r.headers.get("content-type", "").split(";")[0] != "image/jpeg":
        raise HTTPException(503, "La telecamera del server non sta inviando immagini")
    return Response(r.content, media_type="image/jpeg", headers=NO_CACHE)


@router.get("/api/setup/face/analyze")
async def face_analyze_server(_: None = Depends(require_open)):
    return _relay(await _vision("GET", "/setup/analyze"))


@router.post("/api/setup/face/analyze")
async def face_analyze_frame(request: Request, _: None = Depends(require_open)):
    data = await _frame(request)
    if data is None:
        raise HTTPException(415, "Invia un fotogramma della webcam")
    return _relay(await _vision("POST", "/setup/analyze", content=data))


@router.post("/api/setup/face")
async def setup_face(request: Request, _: None = Depends(require_open)):
    kind = str(request.query_params.get("kind") or "")
    if kind not in FACE_KINDS:
        raise HTTPException(400, "Vista del volto non valida")
    data = await _frame(request)
    slug, name = _owner()
    params = {"kind": kind, "name": name}
    if data is None:
        r = await _vision("POST", f"/people/{slug}/views/capture", params=params, timeout=30)
    else:
        r = await _vision("POST", f"/people/{slug}/views", content=data, params=params, timeout=60)
    if r.status_code in (404, 502, 503):
        raise HTTPException(503, UNAVAILABLE)
    if r.status_code != 200:
        return _relay(r)
    done = sorted(set(session_manager.config.get("face_views") or []) | {kind})
    session_manager.record("face_views", done)
    try:
        detail = r.json()
    except ValueError:
        detail = {}
    return JSONResponse({"ok": True, "kind": kind, "views": done, "vision": detail, "source": "browser" if data else "server"},
                        headers=NO_CACHE)

