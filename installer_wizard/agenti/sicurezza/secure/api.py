import socket
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from access import NO_CACHE, require_admin, require_display
from config import STATE_DIR
from enterprise_pki import (
    certs_directory,
    generate_client_bundle,
    generate_enterprise_ca,
    generate_server_certificate,
    get_pki_status,
)

public_routes = APIRouter()
admin_routes = APIRouter()

TLS_DIR = STATE_DIR / "tls"
CA_FILE = TLS_DIR / "ca.pem"
_active = {"port": 0}


def announce(port: int) -> None:
    _active["port"] = port


def active_port() -> int:
    return int(_active["port"])


def _ca_file_path() -> Path:
    std_ca = certs_directory() / "ca.crt"
    if std_ca.exists():
        return std_ca
    std_pem = certs_directory() / "ca.pem"
    if std_pem.exists():
        return std_pem
    if CA_FILE.exists():
        return CA_FILE
    raise HTTPException(404, "Certificato CA non ancora generato")


@public_routes.get("/nuxiva-ca.crt")
async def ca_certificate_crt():
    path = _ca_file_path()
    return FileResponse(path, media_type="application/x-x509-ca-cert", filename="nuxiva-enterprise-ca.crt")


@public_routes.get("/nuxiva-ca.pem")
async def ca_certificate_pem():
    path = _ca_file_path()
    return FileResponse(path, media_type="application/x-pem-file", filename="nuxiva-enterprise-ca.pem")


@public_routes.get("/api/secure/status")
async def secure_status(request: Request):
    require_display(request)
    from https_guard import enforced
    return {
        "https_port": _active["port"],
        "ca": "/nuxiva-ca.crt",
        "host": socket.gethostname(),
        "enforced": enforced() and _active["port"] > 0,
    }


@admin_routes.get("/api/secure/pki/status")
async def admin_pki_status(_: str = Depends(require_admin)):
    st = get_pki_status()
    payload = {
        "has_ca": st.has_ca,
        "ca_subject": st.ca_subject,
        "ca_fingerprint": st.ca_fingerprint,
        "ca_expires_at": st.ca_expires_at,
        "has_server_cert": st.has_server_cert,
        "server_fingerprint": st.server_fingerprint,
        "server_expires_at": st.server_expires_at,
        "sans": st.sans,
        "interfaces": st.interfaces,
        "tailscale_detected": st.tailscale_detected,
        "vpn_detected": st.vpn_detected,
    }
    return JSONResponse(payload, headers=NO_CACHE)


@admin_routes.post("/api/secure/pki/generate")
async def admin_pki_generate(request: Request, _: str = Depends(require_admin)):
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        body = {}

    d = certs_directory()
    ca_pem = d / "ca.pem"
    ca_key = d / "ca.key"

    if not ca_pem.exists() or not ca_key.exists() or body.get("renew_ca", False):
        org = body.get("organization") or "Nuxiva Enterprise OS"
        generate_enterprise_ca(d, organization=org)

    custom_dns: Optional[List[str]] = body.get("custom_dns")
    custom_ips: Optional[List[str]] = body.get("custom_ips")
    include_tailscale: bool = bool(body.get("include_tailscale", True))
    include_vpn: bool = bool(body.get("include_vpn", True))

    generate_server_certificate(
        d,
        ca_pem,
        ca_key,
        custom_dns=custom_dns,
        custom_ips=custom_ips,
        include_tailscale=include_tailscale,
        include_vpn=include_vpn,
    )

    st = get_pki_status()
    return JSONResponse({
        "status": "ok",
        "server_fingerprint": st.server_fingerprint,
        "server_expires_at": st.server_expires_at,
        "sans": st.sans,
    }, headers=NO_CACHE)


@admin_routes.post("/api/secure/pki/client-bundle")
async def admin_pki_client_bundle(request: Request, _: str = Depends(require_admin)):
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        body = {}

    identity = body.get("identity") or f"client-{socket.gethostname()}"
    password = body.get("password") or None

    d = certs_directory()
    ca_pem = d / "ca.pem"
    ca_key = d / "ca.key"

    if not ca_pem.exists() or not ca_key.exists():
        generate_enterprise_ca(d)

    p12_bytes = generate_client_bundle(d, client_identity=identity, password=password)
    return Response(
        content=p12_bytes,
        media_type="application/x-pkcs12",
        headers={
            "Content-Disposition": f'attachment; filename="{identity}.p12"',
            **NO_CACHE,
        },
    )
