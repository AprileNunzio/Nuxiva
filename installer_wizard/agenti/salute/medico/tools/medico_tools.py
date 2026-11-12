from agenti.agent.registry import tool
from agenti.medico.algorithms.reading import may_read, summary
from agenti.people import people


def _person(name: str) -> dict:
    wanted = people.slugify(str(name or ""))
    profile = people.load(wanted)
    if profile:
        return profile
    lowered = str(name or "").strip().lower()
    for p in people.all_profiles(light=True):
        if lowered and lowered in (people.display_name(p).lower(), str(p.get("nickname") or "").lower(),
                                   str(p.get("first_name") or "").lower()):
            return p
    raise ValueError(f"persona «{name}» non trovata in anagrafe")


@tool("medico_parametri",
      "parametri di salute recenti di una persona di casa (battito, respiro, variabilità cardiaca, sonno, passi, recupero)"
      " e segnali da tenere d'occhio; non è una diagnosi",
      {"person": "nome o identificativo della persona"}, full_only=True, agent="medico")
async def medico_parametri(person: str) -> dict:
    profile = _person(person)
    if not may_read(profile):
        raise PermissionError(f"{people.display_name(profile)} non ha dato il consenso a condividere i dati di salute")
    from agenti.medico.vitals import service
    from agenti.medico.vitals.model import METRICS
    return {"person": people.display_name(profile), **summary(service.health_view(profile["slug"]), METRICS)}
