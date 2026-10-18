import time

_last_event: dict | None = None


def emit(status: str, model: dict | None = None, previous: dict | None = None, reason: str = "") -> dict:
    global _last_event
    active = model or {}
    prior = previous or {}
    event = {
        "type": "brain.telemetry.live",
        "timestamp": int(time.time()),
        "status": status,
        "active_route": {"provider_id": "openrouter", "provider_label": "OpenRouter", "model_id": active.get("id", ""),
                         "model_short_name": active.get("name", ""), "pool": active.get("pool", "chat"), "is_free_tier": True},
        "failover_event": {"triggered": bool(prior), "previous_provider": "openrouter" if prior else "",
                            "previous_model": prior.get("id", ""), "reason_i18n_key": reason},
    }
    from features.chat.streaming import push
    from state import store
    push({"type": "brain_route", "route": event})
    store.event("INFO", f"brain.route.{status}: {active.get('id', '')}", "brain")
    _last_event = event
    return event


def current() -> dict | None:
    return dict(_last_event) if _last_event else None
