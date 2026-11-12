from state import store

from agenti.authz import capability, capmap, guard, texts
from agenti.authz import risk as risks
from agenti.authz.policy import Decision, policy
from agenti.authz.principal import Strength, acting
from agenti.authz.risk import Risk

REFUSALS = {
    "role": "Mi dispiace, il profilo di chi mi parla non è autorizzato a questa operazione.",
    "schedule": "Mi dispiace, il tuo profilo è abilitato ad operare solo durante la fascia oraria di servizio.",
    "zone": "Mi dispiace, il tuo profilo non è autorizzato a eseguire comandi in questa stanza o dispositivo.",
    Strength.WEAK: "Per questa operazione devo prima capire chi sei: avvicinati o parlami così posso riconoscerti.",
    Strength.SINGLE: "Per questa operazione devo prima riconoscerti con sicurezza: guarda la telecamera o parlami così riconosco la tua voce.",
    Strength.STRONG: ("È un'operazione delicata: mi serve il riconoscimento di volto e voce insieme, "
                      "oppure chiedila dal pannello di amministrazione."),
}


class Forbidden(PermissionError):

    def __init__(self, decision: Decision) -> None:
        super().__init__(refusal(decision))
        self.decision = decision


NEUTRAL = frozenset({"guest", "room", "owner_data", "rate"})


def refusal(decision: Decision) -> str:
    if decision.code == "role" and guard.speaker_role(acting()) in guard.OUTSIDERS:
        return texts.say("refusal.guest")
    if decision.code in NEUTRAL:
        return texts.say(f"refusal.{decision.code}")
    if decision.code in REFUSALS:
        return REFUSALS[decision.code]
    return REFUSALS.get(decision.needed, REFUSALS[Strength.STRONG])


def _audit(kind: str, name: str, decision: Decision) -> None:
    who = acting()
    store.event("WARN", f"Autorizzazione negata · {kind} «{name}» ({decision.risk.name.lower()}) a "
                        f"{who.slug or 'sconosciuto'} [{who.role}, {who.strength.name.lower()}, {'+'.join(who.factors) or '-'}]: "
                        f"{decision.code}", "authz")
    from agenti.sentinel.collectors.access import collector
    collector.denied(who.slug, who.role, kind, name, str(decision.code or decision.needed))


def check(kind: str, name: str, level: Risk) -> Decision:
    who = acting()
    from agenti.authz.spatial_temporal import validate_spatial_temporal
    st_decision = validate_spatial_temporal(who, who.source)
    if st_decision and not st_decision.allowed:
        _audit(kind, name, st_decision)
        return st_decision
    decision = policy.check(who, level)
    if not decision.allowed:
        _audit(kind, name, decision)
    return decision


def access(kind: str, name: str, capabilities: list[str], level: Risk, args: dict | None = None,
           count: bool = True) -> Decision:
    decision = guard.decide(acting(), capabilities, level, args, count)
    if not decision.allowed:
        _audit(kind, name, decision)
    return decision


def tool(name: str, args: dict | None = None) -> Decision:
    level = risks.of_tool(name)
    if args is not None:
        level = capability.of_call(name, args, level, capability.ha_lookup)
    decision = check("strumento", name, level)
    if not decision.allowed:
        return decision
    return access("strumento", name, capmap.of_call(name, args), level, args)


def plan(plan_data: dict, text: str, lookup) -> Decision:
    level = capability.plan_risk(plan_data, lookup)
    decision = check("casa", text[:80], level)
    if not decision.allowed:
        return decision
    return access("casa", text[:80], capmap.of_plan(plan_data, lookup), level)


def confirm_required(name: str, args: dict | None) -> bool:
    decision = guard.decide(acting(), capmap.of_call(name, args), risks.of_tool(name), args, count=False)
    return decision.allowed and decision.code == "confirm"


def connector(name: str) -> Decision:
    return check("funzione", name, risks.of_connector(name))


def require_tool(name: str, args: dict | None = None) -> None:
    decision = tool(name, args)
    if not decision.allowed:
        raise Forbidden(decision)


def within_role(name: str) -> bool:
    return risks.of_tool(name) <= policy.limit(acting())


def connector_allowed(name: str) -> bool:
    return policy.check(acting(), risks.of_connector(name)).allowed
