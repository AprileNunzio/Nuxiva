from access import is_local


REMOTE_STATE_KEYS = (
    "version", "phase", "phase_label", "installed", "progress", "assistant_name",
    "assistant_gender", "features_rev", "asset_version",
)
BACKGROUND_KEYS = ("paused", "finished", "done", "total", "progress", "current")
BACKGROUND_ITEM_KEYS = ("id", "title", "status", "progress")


def _select(source: dict, keys: tuple[str, ...]) -> dict:
    return {key: source[key] for key in keys if key in source}


def is_host_display(request) -> bool:
    return (
        is_local(request)
        and request.url.hostname in ("127.0.0.1", "::1", "localhost")
        and not any(name in request.headers for name in ("forwarded", "x-forwarded-for", "x-real-ip"))
    )


def remote_state(snapshot: dict, background: dict, face: dict) -> dict:
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
        "audience": {"kind": "uncertain", "nucleus_only": True, "gate": True},
        "presence": {"status": "offline", "people": [], "summary": ""},
        "greeting": None,
        "desk": [],
    }
