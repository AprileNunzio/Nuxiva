import datetime as dt
import ipaddress
import json
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

DEFAULT_CERTS_DIR = Path("/etc/nuxiva/certs")
FALLBACK_CERTS_DIR = Path(__file__).resolve().parents[2] / "data" / "certs"

CA_VALIDITY_DAYS = 3650
LEAF_VALIDITY_DAYS = 397
RENEW_THRESHOLD_DAYS = 30


@dataclass
class NetworkEndpoint:
    kind: str
    value: str
    category: str


@dataclass
class PkiStatus:
    has_ca: bool
    ca_subject: str
    ca_fingerprint: str
    ca_expires_at: str
    has_server_cert: bool
    server_fingerprint: str
    server_expires_at: str
    sans: List[Dict[str, str]]
    interfaces: List[Dict[str, Any]]
    tailscale_detected: bool
    vpn_detected: bool


def certs_directory() -> Path:
    override = os.environ.get("NUXIVA_CERTS_DIR")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    try:
        DEFAULT_CERTS_DIR.mkdir(parents=True, exist_ok=True)
        test_file = DEFAULT_CERTS_DIR / ".write_test"
        test_file.touch()
        test_file.unlink()
        return DEFAULT_CERTS_DIR
    except OSError:
        FALLBACK_CERTS_DIR.mkdir(parents=True, exist_ok=True)
        return FALLBACK_CERTS_DIR


def discover_interfaces() -> List[Dict[str, Any]]:
    interfaces: List[Dict[str, Any]] = []
    try:
        import psutil
        net_addrs = psutil.net_if_addrs()
        for iface_name, entries in net_addrs.items():
            ips = []
            for entry in entries:
                if entry.family in (socket.AF_INET, socket.AF_INET6):
                    addr_clean = entry.address.split("%")[0]
                    if not addr_clean.startswith("169.254."):
                        ips.append(addr_clean)
            is_ts = iface_name.startswith("tailscale")
            is_vpn = iface_name.startswith("wg") or iface_name.startswith("tun")
            interfaces.append({
                "name": iface_name,
                "addresses": ips,
                "is_tailscale": is_ts,
                "is_vpn": is_vpn,
            })
    except Exception:
        pass
    return interfaces


def discover_tailscale_fqdn() -> Optional[str]:
    tailscale_bin = shutil.which("tailscale")
    if not tailscale_bin:
        return None
    try:
        proc = subprocess.run([tailscale_bin, "status", "--json"], capture_output=True, text=True, timeout=3)
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            self_node = data.get("Self", {})
            dns_name = self_node.get("DNSName")
            if dns_name:
                return dns_name.rstrip(".").lower()
    except Exception:
        pass
    return None


def calculate_fingerprint(cert_pem_bytes: bytes) -> str:
    cert = x509.load_pem_x509_certificate(cert_pem_bytes)
    digest = cert.fingerprint(hashes.SHA256())
    return ":".join(f"{b:02X}" for b in digest)


def _safe_write(path: Path, data: bytes, mode: int) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def generate_enterprise_ca(directory: Path, organization: str = "Nuxiva Enterprise OS") -> Tuple[Path, Path]:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
        x509.NameAttribute(NameOID.COMMON_NAME, f"{organization} Root CA"),
    ])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=CA_VALIDITY_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    ca_pem = directory / "ca.pem"
    ca_key = directory / "ca.key"
    ca_crt = directory / "ca.crt"
    cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
    _safe_write(ca_key, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()), 0o600)
    _safe_write(ca_pem, cert_bytes, 0o644)
    _safe_write(ca_crt, cert_bytes, 0o644)
    return ca_pem, ca_key


def generate_server_certificate(
    directory: Path,
    ca_pem: Path,
    ca_key_path: Path,
    custom_dns: Optional[List[str]] = None,
    custom_ips: Optional[List[str]] = None,
    include_tailscale: bool = True,
    include_vpn: bool = True,
) -> Tuple[Path, Path]:
    ca_cert = x509.load_pem_x509_certificate(ca_pem.read_bytes())
    ca_key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)

    dns_names: Set[str] = {"localhost", "nuxiva.local", "nuxiva"}
    ip_addrs: Set[ipaddress.IPv4Address | ipaddress.IPv6Address] = {
        ipaddress.ip_address("127.0.0.1"),
        ipaddress.ip_address("::1"),
    }

    hostname = socket.gethostname().strip().lower()
    if hostname:
        dns_names.add(hostname)

    if custom_dns:
        for name in custom_dns:
            cleaned = name.strip().lower()
            if cleaned:
                dns_names.add(cleaned)

    if custom_ips:
        for raw_ip in custom_ips:
            try:
                ip_addrs.add(ipaddress.ip_address(raw_ip.strip()))
            except ValueError:
                pass

    ifaces = discover_interfaces()
    for iface in ifaces:
        is_ts = iface["is_tailscale"]
        is_vpn = iface["is_vpn"]
        if is_ts and not include_tailscale:
            continue
        if is_vpn and not include_vpn:
            continue
        for raw_addr in iface["addresses"]:
            try:
                ip_obj = ipaddress.ip_address(raw_addr)
                if not ip_obj.is_loopback and not ip_obj.is_unspecified:
                    ip_addrs.add(ip_obj)
            except ValueError:
                pass

    if include_tailscale:
        ts_fqdn = discover_tailscale_fqdn()
        if ts_fqdn:
            dns_names.add(ts_fqdn)

    san_extensions = [x509.DNSName(n) for n in sorted(dns_names)] + [x509.IPAddress(ip) for ip in sorted(ip_addrs, key=str)]

    leaf_key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.timezone.utc)
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Nuxiva Enterprise OS"),
        x509.NameAttribute(NameOID.COMMON_NAME, "Nuxiva Secure Gateway"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=LEAF_VALIDITY_DAYS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.SubjectAlternativeName(san_extensions), critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    server_pem = directory / "server.pem"
    server_key = directory / "server.key"
    san_meta = directory / "san.json"

    _safe_write(server_key, leaf_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()), 0o600)
    _safe_write(server_pem, cert.public_bytes(serialization.Encoding.PEM), 0o644)
    _safe_write(san_meta, json.dumps({
        "names": sorted(dns_names),
        "addresses": sorted(str(ip) for ip in ip_addrs),
    }).encode("utf-8"), 0o644)

    return server_pem, server_key


def generate_client_bundle(
    directory: Path,
    client_identity: str,
    password: Optional[str] = None,
) -> bytes:
    ca_pem = directory / "ca.pem"
    ca_key_path = directory / "ca.key"
    ca_cert = x509.load_pem_x509_certificate(ca_pem.read_bytes())
    ca_key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)

    client_key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.timezone.utc)
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Nuxiva Enterprise Client"),
        x509.NameAttribute(NameOID.COMMON_NAME, client_identity),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=LEAF_VALIDITY_DAYS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(client_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    encryption = (
        serialization.BestAvailableEncryption(password.encode())
        if password
        else serialization.NoEncryption()
    )

    return pkcs12.serialize_key_and_certificates(
        name=client_identity.encode(),
        key=client_key,
        cert=cert,
        cas=[ca_cert],
        encryption_algorithm=encryption,
    )


def get_pki_status(directory: Optional[Path] = None) -> PkiStatus:
    d = directory or certs_directory()
    ca_pem = d / "ca.pem"
    ca_key = d / "ca.key"
    server_pem = d / "server.pem"
    san_file = d / "san.json"

    has_ca = ca_pem.exists() and ca_key.exists()
    ca_subject = ""
    ca_fingerprint = ""
    ca_expires_at = ""

    if has_ca:
        try:
            cert_bytes = ca_pem.read_bytes()
            ca_cert = x509.load_pem_x509_certificate(cert_bytes)
            ca_subject = ca_cert.subject.rfc4514_string()
            ca_fingerprint = calculate_fingerprint(cert_bytes)
            ca_expires_at = ca_cert.not_valid_after_utc.isoformat()
        except Exception:
            has_ca = False

    has_server = server_pem.exists()
    server_fingerprint = ""
    server_expires_at = ""

    if has_server:
        try:
            srv_bytes = server_pem.read_bytes()
            srv_cert = x509.load_pem_x509_certificate(srv_bytes)
            server_fingerprint = calculate_fingerprint(srv_bytes)
            server_expires_at = srv_cert.not_valid_after_utc.isoformat()
        except Exception:
            has_server = False

    sans: List[Dict[str, str]] = []
    if san_file.exists():
        try:
            data = json.loads(san_file.read_text(encoding="utf-8"))
            for name in data.get("names", []):
                cat = "tailscale" if name.endswith(".ts.net") else "dns"
                sans.append({"kind": "dns", "value": name, "category": cat})
            for addr in data.get("addresses", []):
                try:
                    ip = ipaddress.ip_address(addr)
                    if ip.is_loopback:
                        cat = "loopback"
                    elif (isinstance(ip, ipaddress.IPv4Address) and ip.octets[0] == 100 and (ip.octets[1] & 0xc0) == 64) or (isinstance(ip, ipaddress.IPv6Address) and (ip.exploded.startswith("fd7a:115c"))):
                        cat = "tailscale"
                    else:
                        cat = "ip"
                except Exception:
                    cat = "ip"
                sans.append({"kind": "ip", "value": addr, "category": cat})
        except Exception:
            pass

    ifaces = discover_interfaces()
    tailscale_detected = any(i["is_tailscale"] for i in ifaces) or bool(discover_tailscale_fqdn())
    vpn_detected = any(i["is_vpn"] for i in ifaces)

    return PkiStatus(
        has_ca=has_ca,
        ca_subject=ca_subject,
        ca_fingerprint=ca_fingerprint,
        ca_expires_at=ca_expires_at,
        has_server_cert=has_server,
        server_fingerprint=server_fingerprint,
        server_expires_at=server_expires_at,
        sans=sans,
        interfaces=ifaces,
        tailscale_detected=tailscale_detected,
        vpn_detected=vpn_detected,
    )
