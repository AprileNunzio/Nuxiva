from access import is_local


REMOTE_STATE_KEYS = (
    "version", "phase", "phase_label", "installed", "progress", "assistant_name",
    "assistant_gender", "features_rev", "asset_version",
)


def is_host_display(request) -> bool:
    return (
        is_local(request)
        and request.url.hostname in ("127.0.0.1", "::1", "localhost")
        and not any(name in request.headers for name in ("forwarded", "x-forwarded-for", "x-real-ip"))
    )


def remote_state(snapshot: dict) -> dict:
    return {
        **{key: snapshot[key] for key in REMOTE_STATE_KEYS if key in snapshot},
        "audience": {"kind": "uncertain", "nucleus_only": True, "gate": True},
        "presence": {"status": "offline", "people": [], "summary": ""},
        "greeting": None,
        "desk": [],
    }
