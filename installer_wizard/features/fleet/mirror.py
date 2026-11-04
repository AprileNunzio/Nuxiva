import json
import logging

from config import STATE_DIR

from features.fleet import catalog
from features.fleet.model import BULK_MAX, AgentSpec, FleetError, require_id, slug
from features.fleet.service import fleet

log = logging.getLogger("nuxiva.fleet")
SEEN = STATE_DIR / "fleet" / "mirrored.json"
PREFIX = "esperto-"
TEMPLATE_KINDS = {
    "debian": ("system", "sistema"), "home-automation": ("home", "casa"), "football": ("media", "intrattenimento"),
    "solar-energy": ("home", "casa"), "hvac-technician": ("home", "casa"), "network-engineer": ("system", "sistema"),
    "cybersecurity": ("system", "sistema"), "devops-engineer": ("system", "sistema"),
}
DEFAULT_KIND = ("knowledge", "conoscenza")


def _seen() -> set[str]:
    try:
        return set(json.loads(SEEN.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def _remember(ids: set[str]) -> None:
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(sorted(ids)), encoding="utf-8")


def spec_of(expert) -> AgentSpec:
    kind, category = TEMPLATE_KINDS.get(expert.template, DEFAULT_KIND)
    return AgentSpec(id=require_id(f"{PREFIX}{slug(expert.id)}"[:64].rstrip("-")), name=expert.role[:80], kind=kind, category=category,
                     state="active", priority=50, origin="nuxiva", description=expert.specialty[:240], instructions=expert.instructions[:1200])


def mirror(experts: list, service=fleet) -> int:
    done = _seen()
    fresh = []
    for expert in experts:
        try:
            spec = spec_of(expert)
        except FleetError:
            log.warning("Esperto %s non riportato nella flotta", expert.id)
            continue
        if spec.id not in done and not service.store.exists(spec.id):
            fresh.append((spec, expert))
    created = 0
    for start in range(0, len(fresh), BULK_MAX):
        batch = fresh[start:start + BULK_MAX]
        created += service.store.create_many([spec for spec, _ in batch])
    for spec, expert in fresh:
        names = [name for name in expert.tools if catalog.has_tool(name)]
        if names:
            service.store.link(spec.id, "tool", names)
    _remember(done | {spec.id for spec, _ in fresh})
    return created


def sync_all() -> int:
    from features.agent import registry
    from features.experts.store import experts
    registry.refresh()
    return mirror(experts.all())


def add(expert) -> int:
    return mirror([expert])
