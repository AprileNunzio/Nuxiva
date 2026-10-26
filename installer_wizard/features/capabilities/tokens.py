import hashlib
import hmac
import json
import secrets
import time

from config import STATE_DIR

FILE = STATE_DIR / "mcp_tokens.json"
MAX_TOKENS = 20
FAILS: dict[str, list[float]] = {}


def _load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(FILE)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(label: str, risky: bool = False, role: str | None = None, allowed_tools: list[str] | None = None) -> dict:
    from features.authz.access_control import ROLE_GRANTS
    if not isinstance(risky, bool):
        raise ValueError("Indicatore rischio non valido")
    role = ("administrator" if risky else "operator") if role is None else role
    if not isinstance(role, str) or role not in ROLE_GRANTS or (role == "administrator" and not risky):
        raise ValueError("Ruolo non consentito per questo token")
    if allowed_tools is not None and (not isinstance(allowed_tools, list) or len(allowed_tools) > 128 or any(not isinstance(name, str) or not name or len(name) > 128 for name in allowed_tools)):
        raise ValueError("Ambito strumenti non valido")
    data = _load()
    if len(data) >= MAX_TOKENS:
        raise ValueError("Troppi token: revocane qualcuno")
    token = "jv_" + secrets.token_urlsafe(32)
    data[digest(token)[:16]] = {"hash": digest(token), "label": str(label).strip()[:60] or "client", "risky": bool(risky), "role": role, "allowed_tools": allowed_tools, "created": time.time(), "used": 0}
    _save(data)
    return {"token": token, "id": digest(token)[:16]}


def listing() -> list[dict]:
    return [{"id": k, "label": v["label"], "risky": v["risky"], "role": v.get("role", "administrator" if v["risky"] else "operator"), "allowed_tools": v.get("allowed_tools"), "created": v["created"], "used": v["used"]} for k, v in _load().items()]


def revoke(token_id: str) -> bool:
    data = _load()
    found = data.pop(token_id, None) is not None
    if found:
        _save(data)
    return found


def locked(ip: str) -> bool:
    now = time.time()
    FAILS[ip] = [t for t in FAILS.get(ip, []) if now - t < 300]
    return len(FAILS[ip]) >= 8


def check(header: str, ip: str) -> dict | None:
    if locked(ip):
        return None
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    data = _load()
    wanted = digest(token)
    for key, row in data.items():
        if token and hmac.compare_digest(row["hash"], wanted):
            row["used"] = time.time()
            _save(data)
            return {"id": key, "label": row["label"], "risky": row["risky"], "role": row.get("role", "administrator" if row["risky"] else "operator"), "allowed_tools": row.get("allowed_tools")}
    FAILS.setdefault(ip, []).append(time.time())
    return None
