from config import env_get
from functools import partial

from features.agent.registry import tool
from features.fleet import catalog
from features.fleet.model import CATEGORIES, KINDS, LINK_KINDS, FleetError, clean_text
from features.fleet.service import fleet
from features.fleet.store import Filter
from features.team.board import board

fleet_tool = partial(tool, agent="fleet")
LISTED = 15


def _line(record: dict) -> str:
    return f"- {record['id']} ({record['state']}): {record['name']} — {record['description'][:80]}"


@fleet_tool("fleet_find", "cerca tra gli agenti della flotta per nome (prefisso) o per strumento/widget collegato, prima di crearne uno nuovo",
            {"query": "inizio del nome (facoltativo)", "tool": "strumento collegato (facoltativo)", "widget": "widget collegato (facoltativo)"})
async def fleet_find(query: str = "", tool: str = "", widget: str = "") -> str:
    page = fleet.store.list(Filter(prefix=clean_text(query, 80), tool=clean_text(tool, 64), widget=clean_text(widget, 64)), "", LISTED)
    if not page["items"]:
        return "nessun agente corrisponde"
    return "\n".join(_line(item) for item in page["items"]) + ("\n… ce ne sono altri, restringi la ricerca" if page["more"] else "")


@fleet_tool("fleet_create", "crea un nuovo agente della flotta per uno scopo preciso e gli collega gli strumenti e i widget adatti "
            "(se non li indichi li sceglie da solo); se esiste già un agente con quel nome lo restituisce senza duplicarlo",
            {"name": "nome dell'agente", "purpose": "a cosa serve, in una frase", "kind": f"uno tra {', '.join(KINDS)}",
             "category": f"una tra {', '.join(CATEGORIES)}", "instructions": "istruzioni di comportamento (facoltativo)",
             "tools": "lista di nomi di strumenti (facoltativo)", "widgets": "lista di id di widget (facoltativo)",
             "new_widget": "nome di un nuovo widget da creare e collegare (facoltativo)"})
async def fleet_create(name: str, purpose: str, kind: str = "custom", category: str = "altro", instructions: str = "",
                       tools: list | None = None, widgets: list | None = None, new_widget: str = "") -> str:
    if env_get("NUXIVA_FLEET_AUTO_CREATE", "1") == "0":
        return "la creazione automatica di agenti è disattivata nelle impostazioni della flotta: la persona può crearli dall'app Agenti"
    clean_name = clean_text(name, 80)
    existing = fleet.store.list(Filter(prefix=clean_name), "", 1)["items"]
    if existing and existing[0]["name"].lower() == clean_name.lower():
        return f"esiste già: {existing[0]['id']} ({existing[0]['state']})"
    suggested = catalog.suggest(purpose) if not tools and not widgets else {"tools": [], "widgets": []}
    chosen_tools = [str(item) for item in (tools or suggested["tools"])]
    chosen_widgets = [str(item) for item in (widgets or suggested["widgets"])]
    agent_id = fleet.unique_id(clean_name)
    if new_widget:
        from features.forge import assets
        widget_id = fleet.unique_widget_id(new_widget)
        assets.create_widget({"id": widget_id, "name": clean_text(new_widget, 60), "description": clean_text(purpose, 300), "agent": "fleet"})
        chosen_widgets.append(widget_id)
    spec = {"id": agent_id, "name": clean_name, "kind": kind, "category": category, "description": purpose,
            "instructions": instructions, "tools": chosen_tools, "widgets": chosen_widgets}
    try:
        record = fleet.create(spec, "nuxiva", "nuxiva")
    except FleetError as error:
        raise ValueError(error.code)
    board.post("fleet", "tutti", f"nuovo agente «{record['name']}»", "creazione")
    return (f"agente «{record['name']}» creato come {record['id']} con {len(record['tools'])} strumenti e {len(record['widgets'])} widget: "
            f"{', '.join(record['tools'] + record['widgets']) or 'nessun collegamento'}")


@fleet_tool("fleet_attach", "collega a un agente della flotta uno strumento o un widget esistente",
            {"agent": "id dell'agente", "kind": f"uno tra {', '.join(LINK_KINDS)}", "ref": "nome dello strumento o id del widget"})
async def fleet_attach(agent: str, kind: str, ref: str) -> str:
    try:
        fleet.link(agent, kind, [ref], "nuxiva")
    except FleetError as error:
        raise ValueError(error.code)
    return f"{kind} «{ref}» collegato all'agente {agent}"


@fleet_tool("fleet_retire", "mette in archivio un agente della flotta (non lo cancella)", {"agent": "id dell'agente"}, confirm=True)
async def fleet_retire(agent: str) -> str:
    try:
        fleet.update(agent, {"state": "archived"}, "nuxiva")
    except FleetError as error:
        raise ValueError(error.code)
    return f"agente {agent} archiviato"
