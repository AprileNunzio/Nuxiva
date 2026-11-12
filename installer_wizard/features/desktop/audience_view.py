LEVELS = ("public", "household", "personal", "sensitive")
ANONYMOUS_KEYS = ("near", "gaze", "facing")
HOUSEHOLD_SECTIONS = ("home",)
PRIVATE_SECTIONS = ("agency", "background", "logs")
QUIET_SECTIONS = ("live_dialogue",)
SENSITIVE_IDS = frozenset({"vault", "passwords", "bank", "credentials", "secrets"})
SENSITIVE_TOKENS = ("password", "passphrase", "iban", "conto corrente", "cvv", "secret_key", "api_key", "seed phrase")


def requires_double_permission(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    if item.get("sensitivity") == "sensitive" or str(item.get("id") or "") in SENSITIVE_IDS:
        return True
    data = item.get("data")
    if isinstance(data, dict) and (data.get("sensitive") is True or data.get("requires_double_permission") is True):
        return True
    blob = str(data or "").lower()
    return any(tok in blob for tok in SENSITIVE_TOKENS)


def sensitivity(item: dict) -> str:
    level = item.get("sensitivity")
    if level in LEVELS:
        return level
    if requires_double_permission(item):
        return "sensitive"
    return "personal" if item.get("personal") else "public"


def visible(kind: str, level: str, guest_safe: bool, alert: bool, show: dict) -> bool:
    if alert and level == "public":
        return True
    if kind == "authorized":
        return True
    if kind == "mixed":
        return level == "public" or (level == "household" and bool(show.get("trust_guests")))
    if kind == "guest_only":
        return bool(show.get("guest_public")) and guest_safe and level == "public"
    return False


def item_visible(kind: str, item: dict, show: dict) -> bool:
    return visible(kind, sensitivity(item), bool(item.get("guest_safe")), bool(item.get("urgent")), show)


def anonymous_presence(presence: dict) -> dict:
    people = [{"known": False, **{k: p.get(k) for k in ANONYMOUS_KEYS if k in p}}
              for p in (presence or {}).get("people") or [] if isinstance(p, dict)]
    return {"status": (presence or {}).get("status", "offline"), "people": people, "summary": ""}


def redact(snap: dict, audience: dict, show: dict) -> dict:
    kind = (audience or {}).get("kind", "uncertain")
    if kind == "authorized":
        return snap
    out = dict(snap)
    out["desk"] = [i for i in snap.get("desk") or [] if isinstance(i, dict) and item_visible(kind, i, show)]
    out["presence"] = anonymous_presence(snap.get("presence") or {})
    for key in PRIVATE_SECTIONS:
        if key in out:
            out[key] = [] if key == "logs" else None
    if not (kind == "mixed" and show.get("trust_guests")):
        for key in HOUSEHOLD_SECTIONS:
            if key in out:
                out[key] = None
    if kind not in ("mixed", "guest_only"):
        for key in QUIET_SECTIONS:
            if key in out:
                out[key] = None
    return out
