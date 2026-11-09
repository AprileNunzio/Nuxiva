from typing import Literal

from access import is_local, is_private, session_user
from config import env_get
from features.authz.access_control import account, allows
from features.desktop.presence_bridge import gate_enabled


REMOTE_STATE_KEYS = (
    "version", "phase", "phase_label", "installed", "progress", "assistant_name",
    "assistant_gender", "features_rev", "asset_version",
)
BACKGROUND_KEYS = ("paused", "finished", "done", "total", "progress", "current")
BACKGROUND_ITEM_KEYS = ("id", "title", "status", "progress")
PROXY_HEADERS = ("forwarded", "x-forwarded-for", "x-real-ip")
RemoteScope = bool | Literal["browser", "signed_in"]


def _select(source: dict, keys: tuple[str, ...]) -> dict:
    return {key: source[key] for key in keys if key in source}


def is_host_display(request) -> bool:
    return (
        is_local(request)
        and request.url.hostname in ("127.0.0.1", "::1", "localhost")
        and not any(name in request.headers for name in PROXY_HEADERS)
    )


def remote_display_scope(request) -> RemoteScope:
    if is_host_display(request):
        return False
    if (env_get("NUXIVA_KIOSK", "1") == "0" and not gate_enabled() and is_private(request)
            and not any(name in request.headers for name in PROXY_HEADERS)):
        user = session_user(request) if request.url.scheme == "https" else None
        if user and allows(account(user)["role"], "api.admin"):
            return "signed_in"
        return "browser"
    return True


def _browser_widgets(revision: str) -> list[dict]:
    return [{"id": widget, "key": f"browser:{widget}", "rev": revision, "css": True,
             "size": "m", "screen": -1, "data": {}, "sensitivity": "public", "browser_only": True}
            for widget in ("clock", "calculator")]


def remote_state(snapshot: dict, background: dict, face: dict, *, browser: bool = False) -> dict:
    return {
        **_select(snapshot, REMOTE_STATE_KEYS),
        "components": {
            key: _select(component, ("label", "status"))
            for key, component in snapshot.get("components", {}).items()
        },
        "background": {
            **_select(background, BACKGROUND_KEYS),
            "items": [_select(item, BACKGROUND_ITEM_KEYS) for item in background.get("items", [])],
        },
        "face": _select(face, ("avatar", "style", "color")),
        "sounds": {"enabled": False, "cues": []},
        "audience": {"kind": "guest_only" if browser else "uncertain",
                     "nucleus_only": not browser, "gate": not browser, "browser_desk": browser},
        "presence": {"status": "offline", "people": [], "summary": ""},
        "greeting": None,
        "desk": _browser_widgets(str(snapshot.get("asset_version", ""))) if browser else [],
    }
