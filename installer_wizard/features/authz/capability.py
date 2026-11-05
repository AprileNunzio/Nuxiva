from collections.abc import Callable, Iterable

from features.authz.risk import Risk
from features.home_assistant.nlu.calls import is_sensitive
from features.home_assistant.nlu.vocabulary import SENSITIVE_COVERS

EntityLookup = Callable[[str], dict | None]

HA_DOMAIN: dict[str, Risk] = {
    "light": Risk.HOME, "scene": Risk.HOME, "media_player": Risk.HOME, "fan": Risk.HOME, "remote": Risk.HOME,
    "cover": Risk.HOME,
    "climate": Risk.PERSONAL, "water_heater": Risk.PERSONAL, "humidifier": Risk.PERSONAL, "switch": Risk.PERSONAL,
    "input_boolean": Risk.PERSONAL, "lock": Risk.PERSONAL, "alarm_control_panel": Risk.PERSONAL, "siren": Risk.PERSONAL,
    "valve": Risk.PERSONAL, "camera": Risk.PERSONAL, "vacuum": Risk.PERSONAL, "button": Risk.PERSONAL,
    "number": Risk.PERSONAL, "select": Risk.PERSONAL, "input_number": Risk.PERSONAL, "input_select": Risk.PERSONAL,
    "automation": Risk.FILES, "script": Risk.FILES, "homeassistant": Risk.FILES,
}
HA_READ_PRIVATE = frozenset({"person", "device_tracker", "lock", "alarm_control_panel", "camera", "zone"})
HA_UNKNOWN = Risk.FILES
HA_SERVICE_TOOLS = frozenset({"ha_call_service"})
HA_READ_TOOLS = frozenset({"ha_get_state"})


def entity_ids(raw) -> list[str]:
    if isinstance(raw, str):
        items: Iterable = raw.split(",")
    elif isinstance(raw, (list, tuple)):
        items = raw
    else:
        return []
    return [str(x).strip().lower() for x in items if str(x).strip()]


def domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def service_risk(domain: str, service: str, entity: dict) -> Risk:
    if is_sensitive(domain, service, entity):
        return Risk.CRITICAL
    level = HA_DOMAIN.get(domain, HA_UNKNOWN)
    if domain == "cover" and entity.get("device_class") in SENSITIVE_COVERS:
        level = max(level, Risk.PERSONAL)
    return level


def ha_service(args: dict, lookup: EntityLookup) -> Risk:
    service = str(args.get("service") or "").strip().lower()
    declared = str(args.get("domain") or "").strip().lower()
    ids = entity_ids(args.get("entity_id"))
    targets = [(domain_of(eid) or declared, lookup(eid) or {}) for eid in ids] or [(declared, {})]
    levels = [service_risk(domain, service, entity) for domain, entity in targets]
    if declared and declared not in {domain for domain, _ in targets}:
        levels.append(HA_DOMAIN.get(declared, HA_UNKNOWN))
    return max(levels)


def ha_read(args: dict) -> Risk:
    ids = entity_ids(args.get("entity_id"))
    return Risk.PERSONAL if any(domain_of(eid) in HA_READ_PRIVATE for eid in ids) else Risk.HOME


def of_call(name: str, args, base: Risk, lookup: EntityLookup) -> Risk:
    given = args if isinstance(args, dict) else {}
    if name in HA_SERVICE_TOOLS:
        return max(base, ha_service(given, lookup))
    if name in HA_READ_TOOLS:
        return max(base, ha_read(given))
    return base


def lookup_in(entities: dict, states: dict) -> EntityLookup:
    def find(entity_id: str) -> dict | None:
        entity = entities.get(entity_id)
        attrs = (states.get(entity_id) or {}).get("attrs") or {}
        if entity is None and not attrs:
            return None
        merged = dict(entity or {})
        merged["device_class"] = merged.get("device_class") or attrs.get("device_class") or ""
        return merged
    return find


def ha_lookup(entity_id: str) -> dict | None:
    from features.home_assistant.home import brain
    return lookup_in(brain.entities, brain.states)(entity_id)


def plan_risk(plan: dict, lookup: EntityLookup) -> Risk:
    levels = [Risk.INFO]
    for call in plan.get("calls") or []:
        if isinstance(call, dict):
            levels.append(ha_service({"domain": call.get("domain"), "service": call.get("service"),
                                      "entity_id": call.get("entity_ids") or []}, lookup))
    if plan.get("kind") == "query":
        levels.append(ha_read({"entity_id": plan.get("entities") or []}))
    return max(levels)
