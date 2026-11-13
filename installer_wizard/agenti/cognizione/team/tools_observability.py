from agenti.agent import registry
from agenti.team import observability


@registry.tool("team_health", "mostra lo stato di salute della squadra di agenti e della memoria (solo conteggi, nessun dato personale)", {}, agent="agent")
async def team_health() -> str:
    from agenti.desktop.desk import desk
    data = observability.snapshot()
    desk.show("team_health", data, key="agent:team_health", ttl=60)
    squad, engine, memory = data["squad"], data["engine"], data["memory"]
    return (f"{squad['agents']} agenti, {squad['workers']} con worker, {squad['busy']} al lavoro; motore {engine['mode']}; "
            f"memoria {memory['persons']} persone; avvisi: {', '.join(data['alerts']) or 'nessuno'}")
