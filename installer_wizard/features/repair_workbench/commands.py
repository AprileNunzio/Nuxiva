import re

import httpx
from core_client import core
from features.cameras import live
from features.desktop.desk import desk

_START = re.compile(r"\b(?:apri|crea|inizia|avvia|start|open|create)\b", re.I)
_BOARD = re.compile(r"scheda elettronica|ripara\w*.*scheda|aggiust\w*.*scheda|banco riparazioni|repair workbench|repair.*board", re.I)
_FOLLOWUP = re.compile(r"scheda|circuito|componente|tension|misur|resisten|condensator|transistor|saldatur|schema|cosa vedi|che vedi|dove.*(?:inizio|parto)|multimetro|alimentazion|guasto|pin\b", re.I)


async def _request(method, path, **kwargs):
    response = await core.request(method, path, params={"user_id": "user_primary"}, **kwargs)
    response.raise_for_status()
    return response.json()


async def answer(text: str):
    if _START.search(text) and _BOARD.search(text):
        rows = live.listing()
        camera = next((row for row in rows if "banco" in row["name"].lower() or "repair" in row["name"].lower()), None)
        if camera is None:
            return "Non trovo la telecamera del banco: assegna un nome alla sorgente nelle Telecamere e riprova.", {"mode": "face"}
        try:
            project = (await _request("POST", "/api/v1/projects", json={
                "name": "Riparazione Elettronica", "goal": text, "autonomous_247": False,
            }))["project"]
            session = (await _request("POST", "/api/v1/repair-workbench/sessions", json={
                "project_id": project["project_id"], "camera_id": camera["id"],
                "camera_name": camera["name"], "language": "it",
            }))["session"]
        except (httpx.HTTPError, KeyError, ValueError):
            return "Il motore del banco riparazioni non è disponibile. Non ho avviato l'analisi della scheda.", {"mode": "face"}
        desk.scan()
        key = f"repair:{project['project_id']}"
        desk.show("repair_workbench", {"project_id": project["project_id"], "session_id": session["session_id"]},
                  key=key, priority=90, ttl=0)
        desk.fullscreen(key, True)
        return (f"Ho aperto il banco con {camera['name']}. Analizzo i fotogrammi della scheda e mostro componenti, resoconto e schema parziale. "
                "Le ipotesi visive e le tensioni simulate devono essere confermate con misure."), {"mode": "face"}
    active = next((item for item in reversed(list(desk.instances.values())) if item["id"] == "repair_workbench"), None)
    if active and _FOLLOWUP.search(text):
        session_id = active["data"]["session_id"]
        try:
            result = await _request("POST", f"/api/v1/repair-workbench/sessions/{session_id}/chat",
                                    json={"message": text}, timeout=150)
            return result["reply"]["text"], {"mode": "face"}
        except (httpx.HTTPError, KeyError, ValueError):
            return "Lo specialista non è disponibile in questo momento. Il video del banco resta aperto.", {"mode": "face"}
    raise LookupError("repair_workbench")
