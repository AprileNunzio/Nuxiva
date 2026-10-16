from features.experts import routing, service
from features.experts.store import experts

FACE = {"mode": "face"}


async def answer(text: str) -> tuple[str, dict]:
    expert = routing.route(experts.all(), text)
    if expert is None:
        raise LookupError("experts")
    try:
        out = await service.ask(expert.id, text, "it", origin="nuxiva")
    except service.ExpertBusy:
        return f"«{expert.role}» sta già lavorando a un'altra richiesta: riprovi tra poco.", FACE
    if out.get("pending"):
        tool = out["pending"]["tool"]
        return (f"«{expert.role}» vuole usare lo strumento «{tool}» e serve la sua conferma: "
                "la trova nella pagina Agenti della console."), FACE
    return out["text"], FACE
