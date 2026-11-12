import json
import re
from pathlib import Path

from fastapi import HTTPException, Request

from config import STATE_DIR
from agenti.authz.policy import policy
from agenti.authz.principal import Principal, Strength
from agenti.authz.risk import Risk
from agenti.authz.share_grants import valid_share_grants

ACCOUNTS_FILE = STATE_DIR / "authz" / "accounts.json"
ROLE_GRANTS = {
    "administrator": {"*"},
    "operator": {"system.status.read", "logs.read", "logs.export", "devices.read", "mcp.tools.execute",
                 "mcp.resources.read", "files.share.read", "files.share.write"},
    "auditor": {"system.status.read", "logs.read", "logs.export", "mcp.resources.read", "files.share.read"},
    "viewer": {"system.status.read"},
}
ROLE_PROFILES = {"administrator": "owner", "operator": "family", "auditor": "family", "viewer": "guest"}
CAPABILITY_RISKS = {"system.status.read": Risk.INFO, "devices.read": Risk.INFO, "logs.read": Risk.FILES,
                    "logs.export": Risk.FILES, "mcp.tools.execute": Risk.HOME, "mcp.resources.read": Risk.FILES,
                    "files.share.read": Risk.FILES, "files.share.write": Risk.FILES}


def bindings() -> dict:
    try:
        value = json.loads(Path(ACCOUNTS_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "rbac_policy_unavailable") from exc
    if not valid_bindings(value):
        raise HTTPException(503, "rbac_policy_invalid")
    return value


def valid_bindings(value) -> bool:
    return isinstance(value, dict) and len(value) <= 256 and all(
        isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_.@-]{1,64}", name) and isinstance(item, dict) and
        isinstance(item.get("role"), str) and item["role"] in ROLE_GRANTS and isinstance(item.get("nodes", []), list) and
        valid_share_grants(item.get("shares", {})) and
        len(item.get("nodes", [])) <= 128 and all(isinstance(node, str) and (node == "*" or re.fullmatch(r"[A-Za-z0-9._:@-]{1,128}", node)) for node in item.get("nodes", []))
        for name, item in value.items())


def save_bindings(value: dict, actor: str) -> dict:
    if not valid_bindings(value):
        raise HTTPException(422, "invalid_account_bindings")
    previous = bindings().get(actor)
    if (actor in value and (value[actor]["role"] != "administrator" or "*" not in value[actor].get("nodes", []))) or (previous is not None and previous["role"] == "administrator" and actor not in value):
        raise HTTPException(409, "cannot_remove_own_administrator_access")
    path = Path(ACCOUNTS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)
    return value


def account(user: str) -> dict:
    known = bindings().get(user)
    if known is not None:
        return known
    from auth import _is_admin_user
    if _is_admin_user(user):
        return {"role": "administrator", "nodes": ["*"]}
    return {"role": "viewer", "nodes": []}


def principal_for_role(role: str, subject: str) -> Principal:
    return Principal(slug=subject, role=ROLE_PROFILES.get(role, "anonymous"), strength=Strength.STRONG, factors=("credential",))


def allows(role: str, permission: str) -> bool:
    grants = ROLE_GRANTS.get(role, set())
    if "*" not in grants and permission not in grants:
        return False
    return policy.check(principal_for_role(role, "access-check"), CAPABILITY_RISKS.get(permission, Risk.CRITICAL)).allowed


def require_permission(user: str, permission: str, node_id: str | None = None) -> None:
    record = account(user)
    nodes = record.get("nodes", [])
    if not allows(record["role"], permission) or (node_id is not None and "*" not in nodes and node_id not in nodes):
        from state import store
        store.event("WARN", f"RBAC: {permission} denied to {user}", "authz", node_id=node_id)
        raise HTTPException(403, "capability_denied")


def authorize_request(user: str, request: Request) -> None:
    route = request.scope.get("route")
    metadata = getattr(route, "openapi_extra", None) or {}
    permissions = metadata.get("x-nuxiva-capabilities", ["api.admin"])
    for permission in permissions:
        require_permission(user, permission)


def access_summary(user: str) -> dict:
    record = account(user)
    role = record["role"]
    permissions = [permission for permission in ROLE_GRANTS[role] if permission != "*" and allows(role, permission)]
    if "*" in ROLE_GRANTS[role] and allows(role, "api.admin"):
        permissions = ["*"]
    return {"user": user, "role": role, "capabilities": sorted(permissions), "nodes": record.get("nodes", []),
            "share_grants": record.get("shares", {})}


def enrolled(user: str) -> bool:
    return user in bindings()
