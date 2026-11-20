import json

from agenti.agency.tools import Context, Tool, _text
from agenti.people import people

RESTRICTED_ACTIONS = {
    "child": {"gate_unlock", "payment_purchase", "alarm_disarm", "financial_read", "camera_live_all"},
    "guest": {"financial_read", "health_read", "private_diary_read", "gate_unlock", "alarm_disarm", "camera_live_all"},
    "staff": {"financial_read", "health_read", "private_diary_read"},
}


async def _authorize_action_by_role(ctx: Context, args: dict) -> str:
    slug = _text(args, "person_slug", 60)
    action = _text(args, "action_kind", 60)

    p = people.load(slug)
    role = p.get("role", "guest") if p else "guest"
    subrole = p.get("subrole", "") if p else ""
    is_child = subrole == "child" or role == "child" or any(r.get("type") == "figlio" for r in p.get("relations", []) if isinstance(r, dict))
    eff_role = "child" if is_child else role
    blocked = RESTRICTED_ACTIONS.get(eff_role, set())

    is_allowed = action not in blocked
    reason = "Autorizzazione concessa dal profilo di sicurezza Zero-Trust." if is_allowed else f"Azione negata: il profilo «{eff_role}» non possiede il permesso per «{action}»."

    res = {
        "person_slug": slug,
        "role": role,
        "effective_profile": eff_role,
        "action_kind": action,
        "allowed": is_allowed,
        "reason": reason,
    }
    return json.dumps(res, ensure_ascii=False)


async def _privacy_filter_co_presence(ctx: Context, args: dict) -> str:
    active_slug = _text(args, "active_person", 60)
    co_present = args.get("co_present_slugs") or []
    if isinstance(co_present, str):
        co_present = [x.strip() for x in co_present.split(",") if x.strip()]

    has_guest = False
    for slug in co_present:
        p = people.load(slug)
        if (p and p.get("role") in ("guest", "staff")) or slug.lower() == "ospite":
            has_guest = True
            break

    res = {
        "status": "privacy_evaluated",
        "active_person": active_slug,
        "co_present_count": len(co_present),
        "masking_enforced": has_guest,
        "policy": "discretionary_shield" if has_guest else "full_access",
    }
    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "authorize_action_by_role": Tool(
        name="authorize_action_by_role",
        description="Verifica l'autorizzazione di sicurezza Zero-Trust per ospiti, proprietari, figli e collaboratori.",
        args={"person_slug": "string", "action_kind": "string"},
        capability="read",
        run=_authorize_action_by_role,
    ),
    "privacy_filter_co_presence": Tool(
        name="privacy_filter_co_presence",
        description="Valuta la co-presenza di ospiti e collaboratori per mascherare dati sensibili e bacheche private.",
        args={"active_person": "string", "co_present_slugs": "list or string"},
        capability="read",
        run=_privacy_filter_co_presence,
    ),
}
