from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from state import store

from features.authz import risk
from features.authz.policy import policy

admin_routes = APIRouter()


@admin_routes.get("/api/authz/access", openapi_extra={"x-nuxiva-capabilities": ["system.status.read"]})
async def admin_access(user: str = Depends(require_admin)):
    from features.authz.access_control import access_summary
    return access_summary(user)


@admin_routes.get("/api/authz/accounts")
async def admin_accounts(_: str = Depends(require_admin)):
    from features.authz.access_control import ROLE_GRANTS, bindings
    return {"accounts": bindings(), "roles": {role: sorted(grants) for role, grants in ROLE_GRANTS.items()}}


@admin_routes.put("/api/authz/accounts")
async def admin_accounts_update(request: Request, user: str = Depends(require_admin)):
    from features.authz.access_control import save_bindings
    body = await request.json()
    saved = save_bindings(body, user)
    store.event("INFO", f"Account RBAC updated by {user}", "authz")
    return {"accounts": saved}


@admin_routes.get("/api/authz/policy")
async def admin_policy(_: str = Depends(require_admin)):
    return {"policy": policy.export(), "tools": {name: level.name.lower() for name, level in sorted(risk.TOOLS.items())},
            "connectors": {name: level.name.lower() for name, level in sorted(risk.CONNECTORS.items())}}


@admin_routes.put("/api/authz/policy")
async def admin_policy_update(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "Policy non valida")
    saved = policy.save(body)
    store.event("INFO", f"Policy delle autorizzazioni aggiornata da {user}", "authz")
    return {"policy": saved}
