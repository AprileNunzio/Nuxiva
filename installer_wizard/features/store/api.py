from __future__ import annotations

import hmac
import psutil

from access import NO_CACHE, require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from features.store.catalog import find_item
from features.store.repositories import (
    add_repository,
    find_custom_package,
    load_repositories,
    remove_repository,
)
from features.store.service import store_service

public_routes = APIRouter()
admin_routes = APIRouter()


def _verify_origin_and_csrf(request: Request) -> None:
    if request.method in ("POST", "PUT", "DELETE"):
        token = request.headers.get("X-Nuxiva-Request")
        if not token or not hmac.compare_digest(str(token), "1"):
            raise HTTPException(403, "Richiesta non valida")
        origin = request.headers.get("origin")
        if origin:
            host = request.headers.get("host", "")
            if origin.split("://", 1)[-1].rstrip("/") != host:
                raise HTTPException(403, "Origine non autorizzata")


@public_routes.get("/api/store/packages")
@admin_routes.get("/api/store/packages")
async def list_store_packages() -> JSONResponse:
    catalog = store_service.list_all()
    repos = load_repositories()
    disk_free_gb = round(psutil.disk_usage("/").free / (1024**3), 1)
    ram_total_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    return JSONResponse(
        {
            "packages": catalog,
            "repositories": repos,
            "resources": {
                "disk_free_gb": disk_free_gb,
                "ram_total_gb": ram_total_gb,
            },
        },
        headers=NO_CACHE,
    )


@public_routes.get("/api/store/repositories")
@admin_routes.get("/api/store/repositories")
async def list_store_repositories() -> JSONResponse:
    repos = load_repositories()
    return JSONResponse({"repositories": repos}, headers=NO_CACHE)


@public_routes.post("/api/store/repositories")
@admin_routes.post("/api/store/repositories")
async def create_store_repository(
    request: Request,
    _: str = Depends(require_admin),
    __: None = Depends(_verify_origin_and_csrf),
) -> JSONResponse:
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("Corpo richiesta non valido.")
    except Exception as exc:
        raise HTTPException(400, str(exc))

    name = str(body.get("name", "")).strip()
    url = str(body.get("url", "")).strip()
    description = str(body.get("description", "")).strip()
    packages = body.get("packages")

    try:
        new_repo = add_repository(name=name, url=url, description=description, packages=packages)
        return JSONResponse({"ok": True, "repository": new_repo}, status_code=201, headers=NO_CACHE)
    except ValueError as val_err:
        raise HTTPException(400, str(val_err))


@public_routes.delete("/api/store/repositories/{repo_id}")
@admin_routes.delete("/api/store/repositories/{repo_id}")
async def delete_store_repository(
    repo_id: str,
    _: str = Depends(require_admin),
    __: None = Depends(_verify_origin_and_csrf),
) -> JSONResponse:
    try:
        removed = remove_repository(repo_id)
        if not removed:
            raise HTTPException(404, "Repository non trovato.")
        return JSONResponse({"ok": True, "id": repo_id}, headers=NO_CACHE)
    except ValueError as val_err:
        raise HTTPException(400, str(val_err))


@public_routes.get("/api/store/packages/{item_id}")
@admin_routes.get("/api/store/packages/{item_id}")
async def get_store_package(item_id: str) -> JSONResponse:
    item = find_item(item_id)
    if not item:
        custom_pkg = find_custom_package(item_id)
        if not custom_pkg:
            raise HTTPException(404, "Pacchetto non trovato")
        budget_ok, reason = store_service.verify_resource_budget(item_id)
        return JSONResponse(
            {
                "id": custom_pkg["id"],
                "title": custom_pkg["title"],
                "description": custom_pkg["description"],
                "size_gb": custom_pkg["size_gb"],
                "category": custom_pkg["category"],
                "removable": True,
                "source": "custom",
                "repository_id": custom_pkg.get("repository_id"),
                "repository_name": custom_pkg.get("repository_name"),
                "budget_ok": budget_ok,
                "budget_reason": reason,
            },
            headers=NO_CACHE,
        )
    budget_ok, reason = store_service.verify_resource_budget(item_id)
    return JSONResponse(
        {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "size_gb": item.size_gb,
            "category": item.category,
            "removable": item.removable,
            "source": "official",
            "repository_id": "official",
            "repository_name": "Repository Ufficiale Nuxiva",
            "budget_ok": budget_ok,
            "budget_reason": reason,
        },
        headers=NO_CACHE,
    )


@public_routes.post("/api/store/packages/{item_id}/install")
@admin_routes.post("/api/store/packages/{item_id}/install")
async def install_store_package(
    item_id: str,
    request: Request,
    user: str = Depends(require_admin),
    _: None = Depends(_verify_origin_and_csrf),
) -> JSONResponse:
    force = False
    try:
        body = await request.json()
        if isinstance(body, dict):
            force = bool(body.get("force", False))
    except Exception:
        pass
    if not force:
        force = request.query_params.get("force") == "1"

    res = await store_service.install_package(item_id, user, force=force)
    if res.get("advisory"):
        return JSONResponse(res, status_code=200, headers=NO_CACHE)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "install_failed"))
    return JSONResponse(res, headers=NO_CACHE)


@public_routes.post("/api/store/packages/{item_id}/uninstall")
@admin_routes.post("/api/store/packages/{item_id}/uninstall")
async def uninstall_store_package(
    item_id: str,
    request: Request,
    user: str = Depends(require_admin),
    _: None = Depends(_verify_origin_and_csrf),
) -> JSONResponse:
    res = await store_service.uninstall_package(item_id, user)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "uninstall_failed"))
    return JSONResponse(res, headers=NO_CACHE)
