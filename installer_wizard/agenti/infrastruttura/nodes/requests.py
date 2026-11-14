import hashlib
import hmac
import re
import time

from agenti.nodes import trustpolicy, zerotrust
from agenti.nodes.registry import TYPES, clean_id, clean_text, registry

TTL = 15 * 60
MAX_PENDING = 16
_KEY_RE = re.compile(r"^[0-9a-f]{64}$")


def fingerprint(key: str) -> str:
    return f"{int(hashlib.sha256(key.encode()).hexdigest(), 16) % 1_000_000:06d}"


class PairingRequests:

    def __init__(self) -> None:
        self.pending: dict[str, dict] = {}

    def _prune(self) -> None:
        now = time.time()
        self.pending = {k: v for k, v in self.pending.items() if v["expires"] > now}

    def submit(self, body: dict, ip: str) -> dict:
        self._prune()
        node_id = clean_id(body.get("id"))
        pubkey = str(body.get("pubkey") or "")
        key = str(body.get("key") or "")
        if pubkey:
            try:
                code = zerotrust.pairing_code(pubkey)
            except ValueError:
                raise ValueError("node.error.key") from None
            secret, shown = hashlib.sha256(pubkey.encode()).hexdigest(), code
        else:
            if not _KEY_RE.match(key):
                raise ValueError("Chiave del nodo non valida")
            secret, shown = hashlib.sha256(key.encode()).hexdigest(), fingerprint(key)
        if node_id not in self.pending and len(self.pending) >= MAX_PENDING:
            raise ValueError("Troppe richieste in attesa")
        current = self.pending.get(node_id)
        if current and not hmac.compare_digest(current["key"], secret):
            raise PermissionError("Un altro dispositivo sta già chiedendo di abbinarsi con questo nome")
        kind = body.get("type") if body.get("type") in TYPES else "other"
        self.pending[node_id] = {"id": node_id, "name": clean_text(body.get("name")) or node_id, "type": kind,
                                 "room": clean_text(body.get("room")), "ip": ip, "at": time.time(),
                                 "expires": time.time() + TTL, "key": secret, "pubkey": pubkey,
                                 "fingerprint": shown, "approved": False, "token": ""}
        return {"fingerprint": shown, "expires_in": TTL, "signed": bool(pubkey)}

    def approve(self, node_id: str, profile: str = "satellite", allow: bool = False, grants: list | None = None) -> dict:
        self._prune()
        req = self.pending.get(node_id)
        if not req:
            raise KeyError(node_id)
        profile, allow, clean = trustpolicy.validate_change({"pubkey": req["pubkey"]}, profile, allow, grants or [])
        code = registry.new_code()["code"]
        token = registry.pair(code, node_id, req)
        registry.set_trust(node_id, profile, allow, clean)
        req["token"] = token
        req["approved"] = True
        return req

    def pubkey_of(self, node_id: str) -> str:
        self._prune()
        req = self.pending.get(node_id)
        return req["pubkey"] if req else ""

    def is_signed(self, node_id: str) -> bool:
        return bool(self.pubkey_of(node_id))

    def reject(self, node_id: str) -> None:
        self.pending.pop(node_id, None)

    def claim(self, node_id: str, key: str, proven: bool = False) -> str | None:
        self._prune()
        req = self.pending.get(node_id)
        if not req:
            raise PermissionError("Richiesta sconosciuta o scaduta")
        if req["pubkey"]:
            if not proven:
                raise PermissionError("node.error.signature")
        elif not hmac.compare_digest(req["key"], hashlib.sha256(str(key).encode()).hexdigest()):
            raise PermissionError("Richiesta sconosciuta o scaduta")
        if not req["approved"]:
            return None
        self.pending.pop(node_id, None)
        return req["token"]

    def listing(self) -> list[dict]:
        self._prune()
        return [{**{k: v for k, v in r.items() if k not in ("key", "token", "pubkey")}, "signed": bool(r["pubkey"])}
                for r in self.pending.values()
                if not r["approved"]]


requests = PairingRequests()
