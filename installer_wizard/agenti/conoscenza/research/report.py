from datetime import datetime

NO_GUESS = "Rispondi usando SOLO queste fonti e citale; se non bastano a rispondere dillo chiaramente, senza inventare."


def stamp(value: float | None) -> str:
    return datetime.fromtimestamp(value).astimezone().strftime("%d/%m/%Y") if value else "data non indicata"


def render(result: dict) -> str:
    status = result["status"]
    asked = datetime.fromtimestamp(result["at"]).astimezone().strftime("%d/%m/%Y %H:%M")
    if status == "disabled":
        return "La ricerca online è disattivata: non posso verificare questa informazione, quindi non la fornisco."
    if status == "empty":
        return "La domanda per la ricerca è vuota."
    if status == "unavailable":
        return (f"Ricerca online non raggiungibile alle {asked} ({', '.join(sorted(set(result['errors']))) or 'nessuna risposta'}): "
                "non posso verificare questa informazione, quindi non la fornisco. Dillo alla persona senza inventare.")
    if status == "no_results":
        return f"Ricerca online del {asked} per «{result['query']}»: nessuna fonte affidabile trovata. Dillo alla persona senza inventare."
    lines = [f"RICERCA ONLINE del {asked} per «{result['query']}»: {len(result['sources'])} fonti. {NO_GUESS}"]
    for index, source in enumerate(result["sources"], 1):
        lines.append(f"{index}. [{source['reliability']} · {stamp(source['published'])}] {source['title']} — {source['domain']}")
        if source["excerpt"]:
            lines.append(f"   {source['excerpt']}")
        lines.append(f"   {source['url']}")
    return "\n".join(lines)
