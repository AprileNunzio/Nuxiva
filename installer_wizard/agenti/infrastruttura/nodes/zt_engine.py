import hashlib
import json
import re
import struct
import unicodedata

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

MAX_SCOPE = 48
MAX_SEGMENT = 24
MAX_ANNOUNCE = 16 * 1024
MAX_CAPABILITIES = 64
MAX_CORES = 4096
MAX_RAM_MB = 16 * 1024 * 1024
AUTO_MIN_CORES = 4
AUTO_MIN_RAM_MB = 8192
SKEW = 60
DOMAIN = "nuxiva-node-v1"
GENESIS = "0" * 64
SATELLITE = ("audio.capture", "audio.play", "display.render", "sensor.read", "camera.stream", "inference.edge", "telemetry.report")
SECOND_SERVER_EXTRA = ("node.host_full", "compute.lease", "agents.run", "mcp.serve", "storage.replica", "fs.read", "inference.host", "network.relay")
ELEVATED = ("fs.write", "process.exec", "device.control")
FORBIDDEN_DOMAINS = ("admin", "vault", "identity", "users", "audit", "pairing")
SMALL_ORDER = frozenset((
    "0100000000000000000000000000000000000000000000000000000000000000",
    "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
    "0000000000000000000000000000000000000000000000000000000000000000",
    "0000000000000000000000000000000000000000000000000000000000000080",
    "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a",
    "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac03fa",
    "26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05",
    "26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc85",
))
_HEX = re.compile(r"(?:[0-9a-f]{2})*")
_SEGMENT = re.compile(r"[a-z0-9_]{1,24}")
_NONCE = re.compile(r"[A-Za-z0-9_-]+")
_METHOD = re.compile(r"[A-Z]{1,8}")


def valid(scope: str) -> bool:
    if not isinstance(scope, str) or not scope or len(scope.encode()) > MAX_SCOPE:
        return False
    parts = scope.split(".")
    return 2 <= len(parts) <= 3 and all(_SEGMENT.fullmatch(p) for p in parts)


def forbidden(scope: str) -> bool:
    return scope.split(".", 1)[0] in FORBIDDEN_DOMAINS


def base_allowed(mode: str, scope: str) -> bool:
    return scope in SATELLITE or (mode == "second_server" and scope in SECOND_SERVER_EXTRA)


def resolve_mode(profile: str, cpu_cores: int, ram_mb: int, full_host: bool, allowed: bool) -> str:
    if not allowed:
        return "satellite"
    if profile == "second_server":
        return "second_server"
    if profile == "auto" and cpu_cores >= AUTO_MIN_CORES and ram_mb >= AUTO_MIN_RAM_MB and full_host:
        return "second_server"
    return "satellite"


def effective_scopes(mode: str, announced: list[str], grants: list[str]) -> list[str]:
    if len(announced) > 128 or len(grants) > 128:
        raise ValueError("node.error.too_many")
    out = set()
    for scope in announced:
        if not valid(scope) or forbidden(scope):
            continue
        if base_allowed(mode, scope) or (mode == "second_server" and scope in ELEVATED and scope in grants):
            out.add(scope)
    return sorted(out)


def authorize(effective: list[str], requested: str) -> tuple[bool, str]:
    if len(effective) > 128:
        raise ValueError("node.error.too_many")
    if not valid(requested):
        return False, "node.error.scope_invalid"
    if forbidden(requested):
        return False, "node.error.scope_forbidden"
    if requested in effective:
        return True, ""
    return False, "node.error.scope_not_granted"


def _strip(value: str, limit: int) -> str:
    return "".join(c for c in value if unicodedata.category(c) != "Cc")[:limit]


def _uint(value, ceiling: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 0xFFFFFFFFFFFFFFFF:
        raise ValueError("node.error.payload")
    return min(value, ceiling)


def parse_announce(raw: str) -> str:
    if len(raw.encode()) > MAX_ANNOUNCE:
        raise ValueError("node.error.too_large")
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("node.error.payload") from None
    if not isinstance(data, dict):
        raise ValueError("node.error.payload")
    caps = data.get("capabilities", [])
    hardware = data.get("hardware", {})
    if not isinstance(caps, list) or not isinstance(hardware, dict):
        raise ValueError("node.error.payload")
    if len(caps) > MAX_CAPABILITIES:
        raise ValueError("node.error.too_many")
    scopes, rejected = set(), set()
    for item in caps:
        if not isinstance(item, dict) or not isinstance(item.get("scope"), str):
            raise ValueError("node.error.payload")
        scope = item["scope"]
        if valid(scope) and not forbidden(scope):
            scopes.add(scope)
        else:
            rejected.add(_strip(scope, MAX_SCOPE))
    cores = _uint(hardware.get("cpu_cores", 0), MAX_CORES)
    ram = _uint(hardware.get("ram_mb", 0), MAX_RAM_MB)
    ordered = sorted(scopes)
    return json.dumps({"scopes": ordered, "rejected": sorted(rejected), "cpu_cores": cores, "ram_mb": ram,
                       "full_host": "node.host_full" in scopes})


def _key(raw: str) -> Ed25519PublicKey:
    if not isinstance(raw, str) or not _HEX.fullmatch(raw):
        raise ValueError("node.error.hex")
    if len(raw) != 64 or raw in SMALL_ORDER:
        raise ValueError("node.error.key")
    try:
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(raw))
    except ValueError:
        raise ValueError("node.error.key") from None


def fingerprint(raw: str) -> str:
    _key(raw)
    head = hashlib.sha256(bytes.fromhex(raw)).hexdigest()[:12].upper()
    return "-".join(head[i:i + 4] for i in range(0, 12, 4))


def pairing_code(raw: str) -> str:
    _key(raw)
    digest = hashlib.sha256(bytes.fromhex(raw)).digest()
    return f"{int.from_bytes(digest[:8], 'big') % 1_000_000:06d}"


def _field(value: str, minimum: int) -> str:
    if not isinstance(value, str) or len(value.encode()) < minimum or len(value.encode()) > 256 or any(unicodedata.category(c) == "Cc" for c in value):
        raise ValueError("node.error.field")
    return value


def canonical(node: str, method: str, path: str, ts: int, nonce: str, body_sha256: str) -> bytes:
    _field(node, 3)
    _field(path, 1)
    _field(nonce, 16)
    if not _METHOD.fullmatch(method) or len(body_sha256) != 64 or not _HEX.fullmatch(body_sha256) or not _NONCE.fullmatch(nonce):
        raise ValueError("node.error.field")
    return f"{DOMAIN}\n{node}\n{method}\n{path}\n{ts}\n{nonce}\n{body_sha256}".encode()


def verify_request(key_hex: str, signature_hex: str, node: str, method: str, path: str, ts: int, nonce: str,
                   body_sha256: str, now: int) -> None:
    if abs(now - ts) > SKEW:
        raise ValueError("node.error.clock")
    key = _key(key_hex)
    message = canonical(node, method, path, ts, nonce, body_sha256)
    if len(signature_hex) != 128 or not _HEX.fullmatch(signature_hex):
        raise ValueError("node.error.hex" if not _HEX.fullmatch(signature_hex) else "node.error.signature")
    try:
        key.verify(bytes.fromhex(signature_hex), message)
    except InvalidSignature:
        raise ValueError("node.error.signature") from None


def _feed(parts: list[bytes], data: bytes) -> None:
    parts.append(struct.pack(">I", min(len(data), 0xFFFFFFFF)))
    parts.append(data)


def entry_hash(prev: str, seq: int, ts: int, actor: str, node: str, action: str, detail: str) -> str:
    parts: list[bytes] = []
    _feed(parts, prev.encode())
    _feed(parts, struct.pack(">Q", seq))
    _feed(parts, struct.pack(">q", ts))
    for item in (actor, node, action, detail):
        _feed(parts, item.encode())
    return hashlib.sha256(b"".join(parts)).hexdigest()


def audit_seal(prev: str, seq: int, ts: int, actor: str, node: str, action: str, detail: str) -> str:
    actor, node, action, detail = _strip(actor, 64), _strip(node, 64), _strip(action, 48), _strip(detail, 512)
    return json.dumps({"seq": seq, "ts": ts, "actor": actor, "node": node, "action": action, "detail": detail,
                       "prev": prev, "hash": entry_hash(prev, seq, ts, actor, node, action, detail)})


def audit_verify(anchor: str, entries_json: str) -> int:
    try:
        entries = json.loads(entries_json)
    except ValueError:
        raise ValueError("node.error.payload") from None
    if not isinstance(entries, list):
        raise ValueError("node.error.payload")
    if len(entries) > 8192:
        raise ValueError("node.error.too_many")
    prev = anchor
    expected = entries[0].get("seq") if entries and isinstance(entries[0], dict) else None
    for index, entry in enumerate(entries):
        try:
            sound = (entry["seq"] == expected and entry["prev"] == prev
                     and entry["hash"] == entry_hash(entry["prev"], entry["seq"], entry["ts"], entry["actor"],
                                                     entry["node"], entry["action"], entry["detail"]))
        except (KeyError, TypeError, AttributeError, ValueError, struct.error):
            return index
        if not sound:
            return index
        prev = entry["hash"]
        expected = entry["seq"] + 1
    return -1
