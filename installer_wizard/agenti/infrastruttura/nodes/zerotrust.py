import json

import native_core

from agenti.nodes import zt_engine as py


def _call(name: str, python, *args):
    native = native_core.symbol(name)
    if native is not None:
        return native(*args)
    native_core.python_fallback("node_zerotrust")
    return python(*args)


def resolve_mode(profile: str, cpu_cores: int, ram_mb: int, full_host: bool, allowed: bool) -> str:
    return _call("node_resolve_mode", py.resolve_mode, profile, int(cpu_cores), int(ram_mb), bool(full_host), bool(allowed))


def parse_announce(raw: str) -> dict:
    return json.loads(_call("node_parse_announce", py.parse_announce, raw))


def effective_scopes(mode: str, announced: list[str], grants: list[str]) -> list[str]:
    return list(_call("node_effective_scopes", py.effective_scopes, mode, list(announced), list(grants)))


def authorize(effective: list[str], requested: str) -> tuple[bool, str]:
    allowed, code = _call("node_authorize", py.authorize, list(effective), requested)
    return bool(allowed), code


def verify_request(key_hex: str, signature_hex: str, node: str, method: str, path: str, ts: int, nonce: str,
                   body_sha256: str, now: int) -> None:
    _call("node_verify_request", py.verify_request, key_hex, signature_hex, node, method, path, int(ts), nonce, body_sha256, int(now))


def fingerprint(key_hex: str) -> str:
    return _call("node_fingerprint", py.fingerprint, key_hex)


def pairing_code(key_hex: str) -> str:
    return _call("node_pairing_code", py.pairing_code, key_hex)


def audit_seal(prev: str, seq: int, ts: int, actor: str, node: str, action: str, detail: str) -> dict:
    return json.loads(_call("node_audit_seal", py.audit_seal, prev, int(seq), int(ts), actor, node, action, detail))


def audit_verify(anchor: str, entries: list[dict]) -> int:
    return int(_call("node_audit_verify", py.audit_verify, anchor, json.dumps(entries)))
