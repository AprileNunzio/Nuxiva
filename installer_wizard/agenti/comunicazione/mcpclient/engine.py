import ipaddress
import json
import threading
import time
from urllib.parse import urlparse

import native_core
from config import ETC_DIR, STATE_DIR, env_get
from sealed import SealedFile

VAULT = SealedFile(ETC_DIR / "mcp.vault", ETC_DIR / "mcp.key")
SETTINGS_FILE = ETC_DIR / "mcp-settings.json"
POLICY_FILE = ETC_DIR / "mcp-policy.json"
SCOPES_FILE = ETC_DIR / "mcp-scopes.json"
INTERNAL_FILE = ETC_DIR / "mcp-internal.json"
AUDIT_FILE = STATE_DIR / "mcp-audit.log"
AGENT = "mcpclient"
PRINCIPAL = "nuxiva"
CATALOG_TTL = 900
DEFAULT_SCOPES = {AGENT: {"servers": ["*"], "tools": ["*"], "max_risk": "critical"}}
LAN_SUFFIXES = (".local", ".lan", ".home", ".internal")

INTERNAL: dict = {}
WAIT = 10.0

_lock = threading.RLock()
_engine = None
_published = False


def available() -> bool:
    return env_get("NUXIVA_MCP_ENGINE", "rust") != "python" and native_core.symbol("RustMcpEngine") is not None


def _text(path, default: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return default


def _json(path, default):
    try:
        return json.loads(_text(path, ""))
    except ValueError:
        return default


def vault() -> dict:
    try:
        data = VAULT.load()
    except (OSError, ValueError):
        data = {}
    data.setdefault("tokens", {})
    data.setdefault("serial", 0)
    if "signing" not in data:
        secret, public = native_core.symbol("RustMcpEngine").generate_key()
        data["signing"], data["public"] = bytes(secret).hex(), bytes(public).hex()
        VAULT.save(data)
    return data


def consent_ttl() -> float:
    return float(_json(POLICY_FILE, {}).get("consent_ttl_ms", 120_000)) / 1000.0


def get():
    global _engine
    with _lock:
        if _engine is None:
            AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
            built = native_core.symbol("RustMcpEngine")(_text(SETTINGS_FILE, "{}"), _text(POLICY_FILE, "{}"), str(AUDIT_FILE))
            for ident, token in vault()["tokens"].items():
                built.set_secret(ident, token)
            built.set_scopes(json.dumps(_json(SCOPES_FILE, {**DEFAULT_SCOPES, **{i: scope(i) for i in INTERNAL}})))
            built.set_internal(json.dumps(internal_definitions()))
            _engine = built
        return _engine


def scope(ident: str) -> dict:
    return {"servers": [ident], "tools": [f"{ident}.*"], "max_risk": "critical"}


def internal_definitions() -> list:
    found = {ident: build() for ident, build in INTERNAL.items()}
    for item in _json(INTERNAL_FILE, []):
        if isinstance(item, dict) and "id" in item:
            found[item["id"]] = item
    return list(found.values())


def internal_entry(item: dict) -> dict:
    return {"id": item["id"], "enabled": True, "max_risk": "critical", "honor_read_only": True,
            "transport": {"kind": "internal", "name": item["id"]}}


def published() -> bool:
    return _published


def wait_tool(tool_id: str, timeout: float = WAIT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(t["id"] == tool_id and t["state"] == "active" for t in json.loads(get().tools_json())):
            return True
        time.sleep(0.05)
    return False


def rejected():
    return native_core.symbol("McpRejected")


def set_token(ident: str, token: str) -> None:
    with _lock:
        data = vault()
        data["tokens"][ident] = token
        VAULT.save(data)
        get().set_secret(ident, token)


def drop_token(ident: str) -> None:
    with _lock:
        data = vault()
        if data["tokens"].pop(ident, None) is not None:
            VAULT.save(data)
        get().remove_secret(ident)


def local_network(url: str, flag) -> bool:
    if flag is not None:
        return bool(flag)
    host = urlparse(url).hostname or ""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return "." not in host or host.endswith(LAN_SUFFIXES)
    return address.is_private or address.is_loopback


def entry(ident: str, row: dict) -> dict:
    lan = local_network(row["url"], row.get("lan"))
    return {"id": ident, "enabled": bool(row["enabled"]), "max_risk": "critical", "honor_read_only": bool(row["trusted"]),
            "transport": {"kind": "http", "url": row["url"], "secret": ident if row.get("has_token") else None,
                          "network": {"allow_loopback": lan, "allow_private": lan, "ports": []}}}


def publish(rows: dict) -> int:
    global _published
    with _lock:
        data = vault()
        now = int(time.time())
        serial = int(data["serial"]) + 1
        catalog = {"version": 1, "serial": serial, "issued_at": now, "not_after": now + CATALOG_TTL,
                   "servers": [entry(i, r) for i, r in rows.items()] + [internal_entry(d) for d in internal_definitions()]}
        engine = get()
        signed = type(engine).sign_catalog(json.dumps(catalog), bytes.fromhex(data["signing"]))
        engine.apply_catalog(signed, bytes.fromhex(data["public"]), now, int(data["serial"]))
        data["serial"] = serial
        VAULT.save(data)
        _published = True
        return serial


def shutdown() -> None:
    global _engine, _published
    with _lock:
        _published = False
        if _engine is not None:
            _engine.shutdown()
            _engine = None
