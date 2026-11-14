from agenti.agent.registry import tool
from agenti.autonomy import initiative


@tool("nuxiva_ideas", "mostra le idee che Nuxiva ha proposto da sola, con i pulsanti per accettarle o rifiutarle", {})
async def nuxiva_ideas() -> str:
    from agenti.desktop.desk import desk
    data = initiative.snapshot()
    desk.show("ideas", data, key="agent:ideas", ttl=60)
    return f"{len(data['items'])} idee in attesa"
