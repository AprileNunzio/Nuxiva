from agenti.nodes import zerotrust, zt_engine

PROFILES = ("satellite", "second_server", "auto")
GRANDFATHERED = ("compute.lease",)


def legacy(node: dict) -> bool:
    return not node.get("pubkey")


def state(node: dict) -> dict:
    is_legacy = legacy(node)
    profile = node.get("profile") if node.get("profile") in PROFILES else "satellite"
    announce = node.get("announce") if isinstance(node.get("announce"), dict) else None
    allowed = bool(node.get("second_server_allowed")) and not is_legacy
    grants = [g for g in node.get("grants", []) if g in zt_engine.ELEVATED] if allowed else []
    if announce is None:
        announced = list(zt_engine.SATELLITE) if is_legacy else []
        announce = {}
    else:
        announced = list(announce.get("scopes", []))
    mode = zerotrust.resolve_mode(profile, announce.get("cpu_cores", 0), announce.get("ram_mb", 0),
                                  bool(announce.get("full_host")), allowed)
    effective = zerotrust.effective_scopes(mode, announced, grants)
    if is_legacy:
        effective = sorted({*effective, *GRANDFATHERED})
    return {"profile": profile, "mode": mode, "second_server_allowed": allowed, "grants": grants,
            "effective": effective, "announced": announced,
            "denied": sorted(set(announced) - set(effective)), "rejected": list(announce.get("rejected", [])),
            "legacy": is_legacy, "cpu_cores": announce.get("cpu_cores", 0), "ram_mb": announce.get("ram_mb", 0),
            "fingerprint": _fingerprint(node)}


def _fingerprint(node: dict) -> str:
    try:
        return zerotrust.fingerprint(node["pubkey"]) if node.get("pubkey") else ""
    except ValueError:
        return ""


def check(node: dict, scope: str) -> tuple[bool, str]:
    return zerotrust.authorize(state(node)["effective"], scope)


def validate_change(node: dict, profile: str, allow: bool, grants: list) -> tuple[str, bool, list[str]]:
    if profile not in PROFILES:
        raise ValueError("node.error.profile")
    if not isinstance(grants, list) or len(grants) > 8 or not all(isinstance(g, str) and g in zt_engine.ELEVATED for g in grants):
        raise ValueError("node.error.grant")
    clean = sorted(set(grants))
    allow = bool(allow)
    if (profile != "satellite" or allow or clean) and legacy(node):
        raise ValueError("node.error.legacy_identity")
    if profile != "satellite" and not allow:
        raise ValueError("node.error.ceiling_required")
    if clean and not allow:
        raise ValueError("node.error.ceiling_required")
    return profile, allow, clean
