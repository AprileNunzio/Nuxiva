import hashlib
import threading
import time

from fastapi import HTTPException, Request

from agenti.nodes import trustpolicy, zerotrust
from agenti.nodes.audit import audit
from agenti.nodes.registry import registry

NONCE_TTL = 2 * zerotrust.py.SKEW + 5
MAX_NONCES = 20000
REJECT_AUDIT_EVERY = 60.0
MAX_BODY = 12 * 1024 * 1024 + 4096


class ReplayGuard:
    def __init__(self) -> None:
        self.seen: dict[tuple[str, str], float] = {}
        self.lock = threading.Lock()

    def accept(self, node_id: str, nonce: str, now: float) -> bool:
        with self.lock:
            if len(self.seen) >= MAX_NONCES // 2:
                self.seen = {k: v for k, v in self.seen.items() if v > now}
            if len(self.seen) >= MAX_NONCES:
                return False
            key = (node_id, nonce)
            if key in self.seen and self.seen[key] > now:
                return False
            self.seen[key] = now + NONCE_TTL
            return True


replay = ReplayGuard()
_last_reject: dict[str, float] = {}


def _reject(node_id: str, code: str, request: Request) -> None:
    now = time.time()
    if now - _last_reject.get(node_id, 0.0) >= REJECT_AUDIT_EVERY:
        if len(_last_reject) > 256:
            _last_reject.clear()
        _last_reject[node_id] = now
        ip = request.client.host if request.client else "?"
        audit.record("node", node_id, "auth.reject", f"{code} {request.method} {ip}")
    raise HTTPException(401, code)


def request_path(request: Request) -> str:
    raw = request.scope.get("raw_path")
    path = raw.decode("latin-1") if isinstance(raw, (bytes, bytearray)) and raw else request.url.path
    query = request.scope.get("query_string") or b""
    return path.split("?", 1)[0] + (("?" + query.decode("latin-1")) if query else "")


async def verify(request: Request, node_id: str, key_hex: str, path: str | None = None) -> None:
    ts, nonce, sig = (request.headers.get(h, "") for h in ("x-nuxiva-ts", "x-nuxiva-nonce", "x-nuxiva-sig"))
    if int(request.headers.get("content-length") or 0) > MAX_BODY:
        raise HTTPException(413, "node.error.too_large")
    if not ts.lstrip("-").isdigit() or len(ts) > 12:
        _reject(node_id, "node.error.clock", request)
    body = await request.body()
    try:
        now = int(time.time())
        zerotrust.verify_request(key_hex, sig, node_id, request.method.upper(), path or request_path(request), int(ts), nonce,
                                 hashlib.sha256(body).hexdigest(), now)
    except ValueError as exc:
        _reject(node_id, str(exc), request)
    if not replay.accept(node_id, nonce, time.time()):
        _reject(node_id, "node.error.replay", request)


async def guard(request: Request) -> None:
    node_id = request.headers.get("x-nuxiva-node", "")
    node = registry.data["nodes"].get(node_id)
    if node is None or not node.get("pubkey"):
        return
    await verify(request, node_id, node["pubkey"])
    request.state.device_verified = True


def require_scope(node: dict, scope: str) -> None:
    allowed, code = trustpolicy.check(node, scope)
    if not allowed:
        audit.record("node", node["id"], "scope.deny", scope)
        raise HTTPException(403, code)
