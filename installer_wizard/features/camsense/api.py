from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from access import NO_CACHE, require_admin
from state import store as system_store

from features.camsense import service
from features.camsense.model import NAME, SenseError
from features.camsense.store import sensors

admin_routes = APIRouter()


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "invalid_request")
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid_request")
    return body


def _id(sensor_id: str) -> str:
    if not NAME.fullmatch(sensor_id):
        raise HTTPException(404, "not_found")
    return sensor_id


def _fail(exc: SenseError) -> HTTPException:
    return HTTPException(exc.status, exc.code)


@admin_routes.get("/api/camsense")
async def overview(_: str = Depends(require_admin)):
    return JSONResponse({"enabled": service.enabled(), "seconds": service.period(), "cameras": service.cameras(),
                         "sensors": [service.view(r) for r in sensors.all().values()]}, headers=NO_CACHE)


@admin_routes.post("/api/camsense")
async def create(request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    try:
        row = service.create(str(body.get("name") or ""), str(body.get("camera") or ""), body.get("region"))
    except SenseError as exc:
        raise _fail(exc)
    system_store.event("INFO", f"Sensore {row['id']} creato da {user}", "camsense")
    return row


@admin_routes.put("/api/camsense/{sensor_id}")
async def update(sensor_id: str, request: Request, _: str = Depends(require_admin)):
    body = await _body(request)
    try:
        return service.retarget(_id(sensor_id), str(body.get("name") or ""), body.get("region"))
    except SenseError as exc:
        raise _fail(exc)


@admin_routes.delete("/api/camsense/{sensor_id}")
async def remove(sensor_id: str, user: str = Depends(require_admin)):
    try:
        sensors.remove(_id(sensor_id))
    except SenseError as exc:
        raise _fail(exc)
    system_store.event("INFO", f"Sensore {sensor_id} eliminato da {user}", "camsense")
    return {"ok": True}


@admin_routes.post("/api/camsense/{sensor_id}/learn")
async def learn(sensor_id: str, request: Request, _: str = Depends(require_admin)):
    try:
        return await service.learn(_id(sensor_id), str((await _body(request)).get("label") or ""))
    except SenseError as exc:
        raise _fail(exc)


@admin_routes.delete("/api/camsense/{sensor_id}/samples/{label}")
async def forget(sensor_id: str, label: str, _: str = Depends(require_admin)):
    try:
        return service.forget(_id(sensor_id), label)
    except SenseError as exc:
        raise _fail(exc)


@admin_routes.post("/api/camsense/{sensor_id}/check")
async def check(sensor_id: str, _: str = Depends(require_admin)):
    try:
        return await service.check(_id(sensor_id))
    except SenseError as exc:
        raise _fail(exc)


@admin_routes.get("/api/camsense/{sensor_id}/preview")
async def preview(sensor_id: str, _: str = Depends(require_admin)):
    try:
        data = await service.preview(_id(sensor_id))
    except SenseError as exc:
        raise _fail(exc)
    return Response(data, media_type="image/jpeg", headers=NO_CACHE)
