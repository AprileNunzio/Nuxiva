import re
from datetime import date, datetime, timedelta, timezone

from features.sports.catalog import BY_CODE, LIVE, POST, PRE
from features.sports.fetch import get_json

SITE = "https://site.api.espn.com/apis/site/v2/sports"
CORE = "https://site.api.espn.com/apis/v2/sports"
_CODE = re.compile(r"^[a-z0-9_]{2,16}(\.[a-z0-9_]{1,16}){0,2}$")
_ID = re.compile(r"^\d{1,8}$")
_COLOR = re.compile(r"^[0-9a-fA-F]{6}$")


def check_league(code: str) -> str:
    if code not in BY_CODE or not _CODE.match(code):
        raise ValueError("Campionato sconosciuto")
    return code


def check_team(team_id: str) -> str:
    if not _ID.match(str(team_id or "")):
        raise ValueError("Squadra non valida")
    return str(team_id)


def site(league: str) -> str:
    return f"{SITE}/{BY_CODE[check_league(league)].path}"


def core(league: str) -> str:
    return f"{CORE}/{BY_CODE[check_league(league)].path}"


def _score(raw) -> int | None:
    if isinstance(raw, dict):
        raw = raw.get("displayValue", raw.get("value"))
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _team(t: dict) -> dict:
    color = str(t.get("color") or "")
    return {"id": str(t.get("id", "")), "name": str(t.get("displayName") or t.get("name") or "")[:60],
            "short": str(t.get("shortDisplayName") or t.get("displayName") or "")[:30],
            "abbr": str(t.get("abbreviation") or "")[:5], "color": color if _COLOR.match(color) else ""}


def _detail(d: dict, sides: dict) -> dict | None:
    kind = "goal" if d.get("scoringPlay") else "red" if d.get("redCard") else None
    if not kind:
        return None
    who = [str(a.get("displayName", ""))[:40] for a in d.get("athletesInvolved") or []]
    return {"kind": kind, "minute": str((d.get("clock") or {}).get("displayValue") or "")[:8],
            "side": sides.get(str((d.get("team") or {}).get("id", "")), ""), "player": who[0] if who else "",
            "own_goal": bool(d.get("ownGoal")), "penalty": bool(d.get("penaltyKick"))}


def parse_event(e: dict, league: str) -> dict | None:
    comp = (e.get("competitions") or [{}])[0]
    teams = {c.get("homeAway"): c for c in comp.get("competitors") or []}
    if "home" not in teams or "away" not in teams:
        return None
    status = comp.get("status") or e.get("status") or {}
    state = (status.get("type") or {}).get("state", PRE)
    sides = {str(teams[s]["team"].get("id", "")): s for s in ("home", "away")}
    events = [x for x in (_detail(d, sides) for d in comp.get("details") or []) if x]
    out = {"id": str(e.get("id", "")), "league": league, "league_name": BY_CODE[league].name if league in BY_CODE else league,
           "start": str(e.get("date", "")), "state": state if state in (LIVE, PRE, POST) else PRE,
           "clock": str(status.get("displayClock") or "")[:10],
           "detail": str((status.get("type") or {}).get("shortDetail") or "")[:40],
           "venue": str((comp.get("venue") or {}).get("fullName") or "")[:80], "events": events[:20]}
    for side in ("home", "away"):
        out[side] = {**_team(teams[side].get("team") or {}), "score": _score(teams[side].get("score"))}
    return out


async def scoreboard(league: str, day: date | None = None) -> list[dict]:
    check_league(league)
    stamp = (day or datetime.now(timezone.utc).date()).strftime("%Y%m%d")
    today = day is None or day == datetime.now(timezone.utc).date()
    data = await get_json(f"{site(league)}/scoreboard?dates={stamp}", 30 if today else 900)
    return [m for m in (parse_event(e, league) for e in data.get("events") or []) if m]


async def team_fixtures(league: str, team_id: str) -> list[dict]:
    data = await get_json(f"{site(league)}/teams/{check_team(team_id)}/schedule?fixture=true", 1800)
    return [m for m in (parse_event(e, league) for e in data.get("events") or []) if m]


async def team_results(league: str, team_id: str) -> list[dict]:
    data = await get_json(f"{site(league)}/teams/{check_team(team_id)}/schedule", 600)
    rows = [m for m in (parse_event(e, league) for e in data.get("events") or []) if m]
    return [m for m in rows if m["state"] == POST]


async def teams(league: str) -> list[dict]:
    data = await get_json(f"{site(league)}/teams", 86400)
    raw = ((data.get("sports") or [{}])[0].get("leagues") or [{}])[0].get("teams") or []
    return sorted((_team(t.get("team") or {}) for t in raw), key=lambda t: t["name"])


def _stat(stats: dict, *names: str) -> float:
    for name in names:
        value = stats.get(name)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def parse_standings(data: dict) -> list[dict]:
    rows = []
    for child in data.get("children") or [{"standings": data.get("standings") or {}}]:
        group = str(child.get("name") or "")[:40]
        part = []
        for entry in (child.get("standings") or {}).get("entries") or []:
            stats = {s.get("name"): s.get("value") for s in entry.get("stats") or []}
            part.append({**_team(entry.get("team") or {}), "rank": int(_stat(stats, "rank")), "group": group,
                         "played": int(_stat(stats, "gamesPlayed")), "points": int(_stat(stats, "points")),
                         "won": int(_stat(stats, "wins")), "drawn": int(_stat(stats, "ties")),
                         "lost": int(_stat(stats, "losses")), "overtime": int(_stat(stats, "otLosses")),
                         "diff": int(_stat(stats, "pointDifferential", "differential")),
                         "_pct": _stat(stats, "winPercent")})
        part.sort(key=lambda r: (r["rank"] or 999, -r["points"], -r["_pct"], -r["won"]))
        for position, row in enumerate(part, 1):
            row["rank"] = row["rank"] or position
            row.pop("_pct")
        rows += part
    return rows


async def standings(league: str) -> list[dict]:
    return parse_standings(await get_json(f"{core(league)}/standings", 900))


def upcoming(matches: list[dict], horizon_days: int = 21) -> list[dict]:
    now = datetime.now(timezone.utc)
    limit = now + timedelta(days=horizon_days)
    keep = []
    for m in matches:
        try:
            start = datetime.fromisoformat(m["start"].replace("Z", "+00:00"))
        except ValueError:
            continue
        if m["state"] != POST and start <= limit:
            keep.append(m)
    return sorted(keep, key=lambda m: m["start"])
