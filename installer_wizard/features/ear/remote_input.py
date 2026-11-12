from urllib.parse import urlsplit

import auth
from config import env_get
from features.nodes.display_link import display_node


def origin_matches(socket, scheme: str) -> bool:
    host = socket.headers.get("host", "").lower()
    origin = socket.headers.get("origin", "")
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    return bool(host and parsed.scheme == scheme and parsed.netloc.lower() == host
                and not (parsed.path or parsed.query or parsed.fragment))


def local_input(socket) -> bool:
    if not socket.client or socket.client.host not in ("127.0.0.1", "::1"):
        return False
    try:
        host = urlsplit("//" + socket.headers.get("host", "")).hostname
    except ValueError:
        return False
    return host in ("127.0.0.1", "::1", "localhost") and (
        not socket.headers.get("origin") or origin_matches(socket, "http") or origin_matches(socket, "https")
    )


def input_allowed(socket, registered_node: bool) -> bool:
    if local_input(socket):
        return True
    if env_get("NUXIVA_REMOTE_MIC_INPUT", "0") != "1":
        return False
    if socket.url.scheme != "wss":
        return False
    if registered_node and not socket.headers.get("origin"):
        return True
    if not origin_matches(socket, "https"):
        return False
    user = auth.verify(socket.cookies.get(auth.SESSION_COOKIE))
    return bool((user and user != "display") or display_node(socket))
