from fastapi import APIRouter, HTTPException, Depends, Request
from server.core.security_guard.rbac_service import rbac_service
from server.core.security_guard.rbac_models import UserAccount, ROLE_PERMISSIONS_MATRIX, ResourcePermission
from server.core.security_guard.token_provider import token_provider
from server.shared.errors.domain_errors import UnauthorizedException


def require_rbac_admin(request: Request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(401, "authentication_required")
    try:
        token = token_provider.verify_token(header[7:].strip())
    except (UnauthorizedException, ValueError, TypeError) as exc:
        raise HTTPException(401, "invalid_credentials") from exc
    if not isinstance(token, dict):
        raise HTTPException(401, "invalid_credentials")
    claims = token.get("claims", {})
    user_id = claims.get("user_id") if isinstance(claims, dict) else None
    if not isinstance(user_id, str) or not rbac_service.has_permission(user_id, ResourcePermission.RBAC_MANAGE):
        raise HTTPException(403, "rbac_permission_denied")
    return user_id


rbac_router = APIRouter(dependencies=[Depends(require_rbac_admin)])

@rbac_router.get("/rbac/users")
async def list_rbac_users():
    users = rbac_service.list_users()
    return {"status": "success", "users": [u.model_dump() for u in users]}

@rbac_router.post("/rbac/users")
async def upsert_rbac_user(user: UserAccount):
    saved = rbac_service.upsert_user(user)
    return {"status": "success", "user": saved.model_dump()}

@rbac_router.delete("/rbac/users/{user_id}")
async def delete_rbac_user(user_id: str):
    ok = rbac_service.delete_user(user_id)
    if not ok:
        raise HTTPException(status_code=400, detail="Impossibile eliminare l'utente root")
    return {"status": "success"}

@rbac_router.get("/rbac/roles")
async def list_rbac_roles():
    roles_summary = {
        role.value: [perm.value for perm in perms]
        for role, perms in ROLE_PERMISSIONS_MATRIX.items()
    }
    return {"status": "success", "matrix": roles_summary}
