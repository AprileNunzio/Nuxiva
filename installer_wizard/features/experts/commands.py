from features.experts import routing, service
from features.experts.model import Expert
from features.experts.store import experts

FACE = {"mode": "face"}
PIVOT = "it"


async def run(expert: Expert, text: str) -> tuple[str, dict] | None:
    try:
        out = await service.ask(expert.id, text, PIVOT, origin="ceo")
    except service.ExpertBusy:
        return None
    if out.get("pending"):
        tool = out["pending"]["tool"]
        return (f"«{expert.role}» vuole usare lo strumento «{tool}» e serve la sua conferma: "
                "la trova nella pagina Agenti della console."), FACE
    return out["text"], FACE


async def answer(text: str) -> tuple[str, dict]:
    expert = routing.route(experts.all(), text)
    if expert is None:
        raise LookupError("experts")
    found = await run(expert, text)
    if found is None:
        return f"«{expert.role}» sta già lavorando a un'altra richiesta: riprovi tra poco.", FACE
    return found
