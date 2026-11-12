import hashlib
import ssl

from config import STATE_DIR

CA_FILE = STATE_DIR / "tls" / "ca.pem"


def short(digest: str) -> str:
    head = digest[:16].upper()
    return "-".join(head[i:i + 4] for i in range(0, len(head), 4))


def ca_fingerprint() -> str:
    if not CA_FILE.is_file():
        return ""
    return short(hashlib.sha256(ssl.PEM_cert_to_DER_cert(CA_FILE.read_text(encoding="ascii"))).hexdigest())


def https_origin(host: str | None, port: int) -> str:
    if not host or host in ("localhost", "127.0.0.1", "::1") or not port:
        return ""
    return f"https://{host}" if port == 443 else f"https://{host}:{port}"


def ca_pin() -> str:
    if not CA_FILE.is_file():
        return ""
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(CA_FILE.read_text(encoding="ascii"))).hexdigest()
