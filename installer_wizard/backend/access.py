from fastapi import HTTPException, Request

import auth

NO_CACHE = {"Cache-Control": "no-store"}


def is_local(request: Request) -> bool:
    return bool(request.client) and request.client.host in ("127.0.0.1", "::1", "localhost")


def session_user(request: Request) -> str | None:
    return auth.verify(request.cookies.get(auth.SESSION_COOKIE))


def require_admin(request: Request) -> str:
    user = session_user(request)
    if not user:
        raise HTTPException(401, "Accesso richiesto")
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.headers.get("X-Nuxiva-Request") != "1":
        raise HTTPException(403, "Richiesta non valida")
    from features.authz.access_control import authorize_request
    authorize_request(user, request)
    return user


def paired_display(request: Request) -> bool:
    from features.nodes.display_link import display_node
    return display_node(request) is not None


def is_private(request: Request) -> bool:
    if is_local(request):
        return True
    try:
        import ipaddress
        ip = ipaddress.ip_address(request.client.host if request.client else "")
        return ip.is_private or ip.is_link_local
    except (ValueError, TypeError, AttributeError):
        return False


def require_display(request: Request, message: str = "Accesso richiesto") -> None:
    if not (is_local(request) or session_user(request) or paired_display(request)
            or (request.method in ("GET", "HEAD") and is_private(request))):
        raise HTTPException(401, message)


def require_internal(request: Request) -> None:
    if not is_local(request) or request.headers.get("X-Nuxiva-Request") != "1":
        raise HTTPException(403, "Consentito solo in locale")


def lang_of(body: dict) -> str | None:
    return str(body.get("lang") or "")[:8] or None
