import hashlib
import ipaddress
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DOMAIN = "nuxiva-peer-v1"
MAX_PAYLOAD = 16 * 1024
MAX_TTL = 12
MAX_ADDRS = 8
MAX_HOST = 253
ID_RE = re.compile(r"[0-9a-f]{64}")
SIG_RE = re.compile(r"[0-9a-f]{128}")
LABEL_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
FIELDS = {"from", "seq", "ts", "ttl", "payload", "sig"}


def _fail(code: str) -> ValueError:
    return ValueError(f"peer.error.{code}")


def check_addr(raw) -> None:
    if not isinstance(raw, str) or not raw:
        raise _fail("field")
    host, sep, port_text = raw.rpartition(":")
    if not sep or not port_text.isascii() or not port_text.isdigit() or len(port_text) > 5 or int(port_text) > 65535:
        raise _fail("field")
    port = int(port_text)
    bare = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        ip = ipaddress.ip_address(bare)
    except ValueError:
        ip = None
    if ip is not None and (bare is host) == (ip.version == 6) and not (host.startswith("[") and ip.version == 4):
        raise _fail("field")
    if ip is not None:
        if port == 0 or ip.is_unspecified or ip.is_multicast or str(ip) == "255.255.255.255":
            raise _fail("field")
        return
    if host.startswith("[") or port == 0 or not host or len(host) > MAX_HOST:
        raise _fail("field")
    if not all(LABEL_RE.fullmatch(label) for label in host.split(".")):
        raise _fail("field")


def check_addrs(addrs) -> list[str]:
    if not isinstance(addrs, list) or not addrs or len(addrs) > MAX_ADDRS:
        raise _fail("limit")
    for addr in addrs:
        check_addr(addr)
    if len(set(addrs)) != len(addrs):
        raise _fail("field")
    return list(addrs)


def signed_bytes(sender: str, seq: int, ts: int, payload: str) -> bytes:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{DOMAIN}\n{sender}\n{seq}\n{ts}\n{digest}".encode("utf-8")


def verify_signature(envelope, trusted) -> dict:
    if not isinstance(envelope, dict) or set(envelope) != FIELDS:
        raise _fail("payload")
    sender, payload, sig = envelope["from"], envelope["payload"], envelope["sig"]
    seq, ts, ttl = envelope["seq"], envelope["ts"], envelope["ttl"]
    ints = all(isinstance(v, int) and not isinstance(v, bool) for v in (seq, ts, ttl))
    if not isinstance(payload, str) or not ints or seq < 0 or ttl < 0:
        raise _fail("payload")
    if len(payload.encode("utf-8")) > MAX_PAYLOAD or ttl > MAX_TTL:
        raise _fail("limit")
    if not isinstance(sender, str) or sender not in trusted or not ID_RE.fullmatch(sender):
        raise _fail("untrusted")
    if not isinstance(sig, str) or not SIG_RE.fullmatch(sig):
        raise _fail("signature")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(sender)).verify(
            bytes.fromhex(sig), signed_bytes(sender, seq, ts, payload)
        )
    except (InvalidSignature, ValueError) as exc:
        raise _fail("signature") from exc
    try:
        message = json.loads(payload)
    except ValueError as exc:
        raise _fail("payload") from exc
    if not isinstance(message, dict):
        raise _fail("payload")
    return message


def verify_locate(envelope, trusted) -> list[str]:
    message = verify_signature(envelope, trusted)
    if set(message) != {"type", "addrs"} or message["type"] != "locate":
        raise _fail("payload")
    return check_addrs(message["addrs"])
