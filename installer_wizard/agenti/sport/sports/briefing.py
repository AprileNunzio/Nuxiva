import asyncio
from datetime import datetime

from agenti.chat.checkin.contract import fact

TIMEOUT = 3.0
PRIORITY = {"live": 75, "today": 60, "result": 45}


def _profile() -> dict | None:
    from agenti.chat import context as request_context
    from agenti.people import identity
    return identity.current(request_context.voice.get()) or identity.owner()


def _start(match: dict) -> float | None:
    try:
        return datetime.fromisoformat(match["start"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError):
        return None


async def facts() -> list[dict]:
    from agenti.sports.prefs import HOUSEHOLD, prefs
    from agenti.sports.spotlight import team_card
    profile = _profile()
    teams = (prefs.get(profile["slug"]) if profile else {}).get("teams") or prefs.get(HOUSEHOLD).get("teams") or []
    cards = await asyncio.gather(*(team_card(t) for t in teams[:3]))
    out = []
    for card in (c for c in cards if c and c["kind"] in PRIORITY):
        m, team = card["match"], card["team"]
        rival = m["away"] if m["home"]["id"] == team["id"] else m["home"]
        at = _start(m)
        local = datetime.fromtimestamp(at).strftime("%H:%M") if at else ""
        score = f"{m['home'].get('score') or 0}-{m['away'].get('score') or 0}"
        out.append(fact(f"sport_{team['id']}", "sport", "interest", PRIORITY[card["kind"]], 900, f"sport_{card['kind']}",
                        {"team": team["name"], "rival": rival.get("name", ""), "time": local, "score": score},
                        starts_at=at, terms=["partita", "match", "calcio", "football", "partido", team["name"]]))
    return out
