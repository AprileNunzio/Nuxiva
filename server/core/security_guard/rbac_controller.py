from fastapi import APIRouter, HTTPException
from server.core.security_guard.rbac_service import rbac_service
from server.core.security_guard.rbac_models import UserAccount, ROLE_PERMISSIONS_MATRIX

rbac_router = APIRouter()

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
