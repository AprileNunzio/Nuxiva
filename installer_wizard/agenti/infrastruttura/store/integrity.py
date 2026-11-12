from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any, Optional

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    HAS_CRYPTO = True
except (ImportError, ModuleNotFoundError, Exception):
    HAS_CRYPTO = False

ALLOWED_CAPABILITIES = {
    "local_storage",
    "webgl2",
    "audio_output",
    "audio_stream_capture",
    "network_fetch",
    "system_telemetry",
    "tray_badge",
    "vad_filter",
    "local_weights",
    "tree_search",
    "branch_pruning",
    "offline_weights",
    "portfolio_analytics",
    "stress_test",
    "risk_alert",
    "telemetry_read",
}

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{2,64}$")


def verify_sha256_checksum(data: bytes, expected_checksum: str) -> bool:
    clean_expected = expected_checksum.strip().lower()
    if clean_expected.startswith("sha256:"):
        clean_expected = clean_expected[7:]
    elif clean_expected.startswith("sha256-"):
        clean_expected = clean_expected[7:]
    if len(clean_expected) != 64 or not re.match(r"^[0-9a-f]{64}$", clean_expected):
        return False
    computed = hashlib.sha256(data).hexdigest()
    return hmac.compare_digest(computed, clean_expected)


def verify_ed25519_signature(data: bytes, signature_hex: str, public_key_hex: str) -> bool:
    if not HAS_CRYPTO:
        return True
    try:
        sig_bytes = bytes.fromhex(signature_hex.strip())
        pub_bytes = bytes.fromhex(public_key_hex.strip())
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, data)
        return True
    except Exception:
        return False


def validate_package_security_contract(pkg: dict[str, Any]) -> tuple[bool, Optional[str]]:
    raw_id = str(pkg.get("id") or pkg.get("raw_id") or "").strip()
    if not SAFE_ID_REGEX.match(raw_id):
        return False, "package_id_invalid_format"

    title = str(pkg.get("title") or "").strip()
    if not title or len(title) > 100:
        return False, "package_title_length_exceeded"

    category = str(pkg.get("category") or "productivity").strip()
    if len(category) > 40:
        return False, "package_category_invalid"

    size_gb = float(pkg.get("size_gb", 0.5))
    if size_gb <= 0 or size_gb > 1000:
        return False, "package_size_out_of_bounds"

    caps = pkg.get("capabilities")
    if caps is not None:
        if not isinstance(caps, list):
            return False, "capabilities_must_be_list"
        for cap in caps:
            if not isinstance(cap, str) or len(cap) > 64:
                return False, "capability_invalid_format"

    allowed_hosts = pkg.get("allowed_hosts")
    if allowed_hosts is not None:
        if not isinstance(allowed_hosts, list):
            return False, "allowed_hosts_must_be_list"
        for host in allowed_hosts:
            if not isinstance(host, str) or not re.match(r"^[a-zA-Z0-9.-]{3,128}$", host):
                return False, "allowed_host_invalid"

    checksum = pkg.get("checksum") or pkg.get("integrity")
    if checksum:
        c_str = str(checksum).strip().lower()
        if c_str.startswith("sha256:") or c_str.startswith("sha256-"):
            c_str = c_str[7:]
        if len(c_str) != 64 or not re.match(r"^[0-9a-f]{64}$", c_str):
            return False, "invalid_sha256_checksum"

    return True, None
