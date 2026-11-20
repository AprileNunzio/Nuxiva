import json

from agenti.agency.project_room import assign_pair_to_desk, get_project_room
from agenti.agency.project_scaffolder import project_scaffolder
from agenti.agency.tools import Context, Tool, _text


async def _scaffold_modular_project(ctx: Context, args: dict) -> str:
    name = _text(args, "project_name", 120) or "Nuovo Progetto Modulare"
    domain = _text(args, "domain", 80) or "tech"
    stack = args.get("stack") if isinstance(args.get("stack"), dict) else None
    caps = args.get("capabilities") if isinstance(args.get("capabilities"), list) else None

    scaffold = project_scaffolder.scaffold_modular_architecture(
        project_name=name,
        domain=domain,
        stack=stack,
        capabilities=caps,
    )
    verification = project_scaffolder.verify_clean_architecture(scaffold)
    return json.dumps({
        "status": "scaffolded",
        "scaffold": scaffold,
        "verification": verification,
    }, ensure_ascii=False)


async def _assign_pair_programming_desk(ctx: Context, args: dict) -> str:
    proj_id = _text(args, "project_id", 80)
    desk_idx = int(args.get("desk_index") or 0)
    second_role = _text(args, "second_role", 80)

    room = get_project_room(proj_id)
    if not room:
        return json.dumps({"status": "error", "message": f"Stanza progetto «{proj_id}» non trovata."})

    desks = room.get("desks", [])
    target_desk = next((d for d in desks if d.get("index") == desk_idx), None)
    if not target_desk:
        return json.dumps({"status": "error", "message": f"Banco con indice {desk_idx} non trovato."})

    updated_desk = assign_pair_to_desk(target_desk, second_role)
    room["pair_programming_desks_count"] = sum(1 for d in desks if d.get("is_pair_programming"))

    return json.dumps({
        "status": "assigned",
        "project_id": proj_id,
        "desk_index": desk_idx,
        "agents": updated_desk.get("agents", []),
        "pair_mode": updated_desk.get("is_pair_programming", False),
        "workstations_count": len(updated_desk.get("workstations", [])),
    }, ensure_ascii=False)


async def _verify_project_architecture(ctx: Context, args: dict) -> str:
    scaffold = args.get("scaffold") if isinstance(args.get("scaffold"), dict) else {}
    if not scaffold:
        return json.dumps({"status": "error", "message": "Manifest di scaffolding assente."})
    verif = project_scaffolder.verify_clean_architecture(scaffold)
    return json.dumps({"status": "verified", "report": verif}, ensure_ascii=False)


TOOLS = {
    "scaffold_modular_project": Tool(
        name="scaffold_modular_project",
        description="Genera l'architettura modulare di un nuovo progetto o modulo: separa rigorosamente backend e frontend, definisce contratti API REST/OpenAPI, manifesti server MCP con tools per ogni capacità e alloca banchi per pair programming.",
        args={"project_name": "string", "domain": "optional string", "stack": "optional object", "capabilities": "optional list"},
        capability="write",
        run=_scaffold_modular_project,
    ),
    "assign_pair_programming_desk": Tool(
        name="assign_pair_programming_desk",
        description="Alloca contemporaneamente due agenti alla stessa scrivania della stanza di progetto per sessioni di pair programming e revisione congiunta.",
        args={"project_id": "string", "desk_index": "integer", "second_role": "string"},
        capability="execute",
        run=_assign_pair_programming_desk,
    ),
    "verify_project_architecture": Tool(
        name="verify_project_architecture",
        description="Verifica che un progetto rispetti la separazione frontend/backend, la presenza di contratti API, l'integrazione di tool MCP e la sicurezza Zero-Trust.",
        args={"scaffold": "object"},
        capability="read",
        run=_verify_project_architecture,
    ),
}
