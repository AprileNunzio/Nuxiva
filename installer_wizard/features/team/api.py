from fastapi import APIRouter, Depends, HTTPException, Request

from access import require_admin
from features.agent import registry as tools
from features.team import roster
from features.team.board import board
from features.team.control import control
from state import store

public_routes = APIRouter()
admin_routes = APIRouter()
CONSOLE = "console"


def _people() -> list[dict]:
    from features.people import people
    return [{"slug": p["slug"], "name": p.get("name") or p["slug"]} for p in people.all_profiles(light=True)]


def _desk():
    from features.desktop.desk import desk
    return desk


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "Richiesta non valida")
    if not isinstance(body, dict):
        raise HTTPException(400, "Richiesta non valida")
    return body


def _agent(agent_id: str) -> str:
    if agent_id not in roster.ids():
        raise HTTPException(404, "Agente sconosciuto")
    return agent_id


def _overview() -> dict:
    desk = _desk()
    desk.scan()
    from features.forge import recipes
    doc = roster.document()
    doc["tools"] = sorted((roster.tool_row(t) | {"custom": t["name"] in recipes.CUSTOM} for t in tools.TOOLS.values()),
                          key=lambda t: t["name"])
    doc["widgets"] = [{"id": m["id"], "name": m.get("name", m["id"]), "icon": m.get("icon", ""), "source": m.get("source", "system"),
                       "agent": roster.widget_owner(m), "default_agent": str(m.get("agent") or "desktop"),
                       "people": control.widget_people(m["id"]), "enabled": desk.enabled(m["id"]), "personal": bool(m.get("personal"))}
                      for m in sorted(desk.widgets.values(), key=lambda m: m["id"])]
    doc["people"] = _people()
    doc["recipes"] = list(recipes.CUSTOM.values())
    return doc


@admin_routes.get("/api/team")
async def team(_: str = Depends(require_admin)):
    return _overview()


@admin_routes.get("/api/team/{agent_id}")
async def member(agent_id: str, _: str = Depends(require_admin)):
    try:
        return roster.profile(roster.find(agent_id))
    except KeyError as exc:
        raise HTTPException(404, str(exc))


@admin_routes.put("/api/team/{agent_id}")
async def update_member(agent_id: str, request: Request, user: str = Depends(require_admin)):
    body = await _body(request)
    try:
        control.set_agent(_agent(agent_id), {k: body[k] for k in ("priority", "instructions") if k in body})
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Agente {agent_id} aggiornato da {user}", "team")
    return roster.profile(agent_id)


@admin_routes.post("/api/team/{agent_id}/message")
async def message_member(agent_id: str, request: Request, user: str = Depends(require_admin)):
    text = str((await _body(request)).get("text") or "").strip()
    if not text or len(text) > 400:
        raise HTTPException(400, "Messaggio non valido")
    row = board.post(CONSOLE, _agent(agent_id), f"{user}: {text}", "compito")
    return {"message": row, "inbox": len(board.inbox.get(agent_id, []))}


@admin_routes.put("/api/team/tools/{name}")
async def update_tool(name: str, request: Request, user: str = Depends(require_admin)):
    if name not in tools.TOOLS:
        raise HTTPException(404, "Strumento sconosciuto")
    body = await _body(request)
    if name.startswith(("team_", "agent_")) and body.get("enabled") is False:
        raise HTTPException(409, "Gli strumenti di coordinamento non si possono spegnere")
    try:
        control.set_tool(name, body, set(roster.ids()))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Strumento {name} aggiornato da {user}", "team")
    return roster.tool_row(tools.TOOLS[name])


@admin_routes.put("/api/team/widgets/{wid}")
async def update_widget(wid: str, request: Request, user: str = Depends(require_admin)):
    if wid not in _desk().widgets:
        raise HTTPException(404, "Widget sconosciuto")
    try:
        row = control.set_widget(wid, await _body(request), set(roster.ids()), {p["slug"] for p in _people()})
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    _desk().publish()
    store.event("INFO", f"Widget {wid} associato da {user}", "team")
    return row


@admin_routes.post("/api/team/agents")
async def create_agent(request: Request, user: str = Depends(require_admin)):
    from features.forge import assets
    body = await _body(request)
    try:
        manifest = assets.create_feature({k: body.get(k) for k in ("id", "name", "description", "capabilities", "category", "icon")}, "user")
        if body.get("instructions") or body.get("priority") is not None:
            control.set_agent(manifest["id"], {k: body[k] for k in ("priority", "instructions") if k in body})
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    board.post(CONSOLE, "tutti", f"nuovo agente «{manifest['name']}» creato da {user}", "creazione")
    store.event("INFO", f"Agente {manifest['id']} creato da {user}", "team")
    return roster.profile(manifest["id"])


@admin_routes.delete("/api/team/agents/{agent_id}")
async def delete_agent(agent_id: str, user: str = Depends(require_admin)):
    from features.forge import assets
    if not assets.delete_feature(_agent(agent_id)):
        raise HTTPException(409, "Si possono eliminare solo gli agenti creati da te o da Nuxiva")
    control.forget_agent(agent_id)
    store.event("INFO", f"Agente {agent_id} eliminato da {user}", "team")
    return {"ok": True}


@admin_routes.post("/api/team/tools")
async def create_tool(request: Request, user: str = Depends(require_admin)):
    from features.forge import recipes
    body = await _body(request)
    if body.get("agent") and body["agent"] not in roster.ids():
        raise HTTPException(400, "Agente non valido")
    try:
        spec = recipes.save({k: body.get(k) for k in ("name", "description", "params", "steps", "agent")})
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc))
    board.post(CONSOLE, "tutti", f"nuovo strumento «{spec['name']}» creato da {user}", "creazione")
    return roster.tool_row(tools.TOOLS[spec["name"]])


@admin_routes.delete("/api/team/tools/{name}")
async def delete_tool(name: str, user: str = Depends(require_admin)):
    from features.forge import recipes
    if not recipes.remove(name):
        raise HTTPException(409, "Si possono eliminare solo gli strumenti creati da te o da Nuxiva")
    store.event("INFO", f"Strumento {name} eliminato da {user}", "team")
    return {"ok": True}


@admin_routes.post("/api/team/widgets")
async def create_widget(request: Request, user: str = Depends(require_admin)):
    from features.forge import assets
    body = await _body(request)
    try:
        manifest = assets.create_widget({k: body.get(k) for k in ("id", "name", "description", "icon", "size", "priority", "personal", "agent")})
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, str(exc))
    store.event("INFO", f"Widget {manifest['id']} creato da {user}", "team")
    return manifest


@admin_routes.delete("/api/team/widgets/{wid}")
async def delete_widget(wid: str, user: str = Depends(require_admin)):
    from features.forge import assets
    if not assets.delete_widget(wid):
        raise HTTPException(409, "Si possono eliminare solo i widget creati da te o da Nuxiva")
    store.event("INFO", f"Widget {wid} eliminato da {user}", "team")
    return {"ok": True}
