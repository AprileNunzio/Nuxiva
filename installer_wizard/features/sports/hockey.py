from datetime import date, datetime, timedelta, timezone

from features.sports import football
from features.sports.catalog import POST
from features.sports.fetch import get_json

LEAGUE = "nhl"
LEAGUE_NAME = "NHL"
SITE = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl"
CORE = "https://site.api.espn.com/apis/v2/sports/hockey/nhl"


def _tag(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["league"] = LEAGUE
        row["league_name"] = LEAGUE_NAME
    return rows


def _events(data: dict) -> list[dict]:
    return _tag([m for m in (football.parse_event(e, LEAGUE) for e in data.get("events") or []) if m])


async def scoreboard(day: date | None = None) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    stamp = (day or today).strftime("%Y%m%d")
    return _events(await get_json(f"{SITE}/scoreboard?dates={stamp}", 30 if day in (None, today) else 900))


async def recent_games() -> list[dict]:
    today = datetime.now(timezone.utc).date()
    days = (today - timedelta(days=1), today)
    boards = [await scoreboard(day) for day in days]
    return sorted((m for board in boards for m in board), key=lambda m: m["start"])


async def team_fixtures(team_id: str) -> list[dict]:
    return _events(await get_json(f"{SITE}/teams/{football.check_team(team_id)}/schedule?fixture=true", 1800))


async def team_results(team_id: str) -> list[dict]:
    rows = _events(await get_json(f"{SITE}/teams/{football.check_team(team_id)}/schedule", 600))
    return [m for m in rows if m["state"] == POST]


async def teams() -> list[dict]:
    data = await get_json(f"{SITE}/teams", 86400)
    raw = ((data.get("sports") or [{}])[0].get("leagues") or [{}])[0].get("teams") or []
    return _tag(sorted((football._team(t.get("team") or {}) for t in raw), key=lambda t: t["name"]))


def _stat(entry: dict, name: str) -> float:
    for s in entry.get("stats") or []:
        if s.get("name") == name and isinstance(s.get("value"), (int, float)):
            return float(s["value"])
    return 0.0


async def standings() -> list[dict]:
    data = await get_json(f"{CORE}/standings", 900)
    rows = []
    for child in data.get("children") or []:
        conference = str(child.get("name") or "")[:40]
        entries = sorted(((child.get("standings") or {}).get("entries") or []), key=lambda e: (-_stat(e, "points"), -_stat(e, "wins")))
        for rank, entry in enumerate(entries, 1):
            rows.append({**football._team(entry.get("team") or {}), "conference": conference, "rank": rank,
                         "played": int(_stat(entry, "gamesPlayed")), "points": int(_stat(entry, "points")),
                         "won": int(_stat(entry, "wins")), "lost": int(_stat(entry, "losses")),
                         "overtime": int(_stat(entry, "otLosses")), "league": LEAGUE})
    return rows
