import asyncio
import re
import time
import unicodedata
from datetime import datetime, timedelta, timezone

from features.sports import football, spotlight, understand
from features.sports.catalog import BY_CODE, F1_LABELS, INDEXED, LEAGUES, TEAM_ALIASES, League
from features.sports.fetch import SportsUnavailable
from features.sports.prefs import prefs
from features.sports.speech import day_speech, f1_speech, match_speech, table_speech

FACE = {"mode": "face"}


def norm(text: str) -> str:
    flat = unicodedata.normalize("NFKD", str(text or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", flat).strip()


_INDEX: dict = {"at": 0.0, "teams": []}
INDEX_EVERY = 86400


async def refresh_index() -> None:
    if time.time() - _INDEX["at"] < INDEX_EVERY and _INDEX["teams"]:
        return
    rows: list[dict] = []
    lists = await asyncio.gather(*(football.teams(code) for code in INDEXED), return_exceptions=True)
    for code, teams in zip(INDEXED, lists):
        if isinstance(teams, list):
            rows += [{**t, "league": code, "league_name": BY_CODE[code].name} for t in teams]
    if rows:
        _INDEX.update(at=time.time(), teams=rows)
    elif not _INDEX["teams"]:
        raise SportsUnavailable("elenco squadre non raggiungibile")


def known_teams() -> list[dict]:
    rows = {(t["league"], t["id"]): t for t in _INDEX["teams"]}
    rows.update(prefs.followed_teams())
    return list(rows.values())


def find_team(text: str, teams: list[dict]) -> dict | None:
    words = f" {norm(text)} "
    for alias, target in TEAM_ALIASES.items():
        words = words.replace(f" {alias} ", f" {alias} {target} ")
    best = None
    for t in teams:
        for label in {norm(t["name"]), norm(t.get("short", ""))}:
            if len(label) >= 4 and f" {label} " in words and (not best or len(label) > best[0]):
                best = (len(label), t)
    return best[1] if best else None


def find_league(text: str) -> League | None:
    flat = f" {norm(text)} "
    best = None
    for league in LEAGUES:
        for label in league.labels:
            key = norm(label)
            if f" {key} " in flat and (not best or len(key) > best[0]):
                best = (len(key), league)
    return best[1] if best else None


def find_f1(text: str) -> bool:
    flat = f" {norm(text)} "
    return any(f" {label} " in flat for label in F1_LABELS)


def _desk():
    from features.desktop.desk import desk
    return desk


async def _f1(want: str) -> tuple[str, dict]:
    if want == "f1_standings":
        card = await spotlight.f1_standings_card()
    else:
        card = await spotlight.f1_card() or await spotlight.f1_standings_card()
    _desk().show("f1_race", card, key="sport:f1", ttl=120, intent=True)
    return f1_speech(card), FACE


async def _table(league: str, team: dict | None) -> tuple[str, dict]:
    card = await spotlight.standings_card(league, {team["id"]} if team else set())
    _desk().show("sport_table", card, key=f"sport:table:{league}", ttl=120, intent=True)
    return table_speech(card, team), FACE


async def _day(league: str) -> tuple[str, dict]:
    today = datetime.now(timezone.utc).date()
    boards = await asyncio.gather(football.scoreboard(league, today - timedelta(days=1)), football.scoreboard(league))
    games = sorted((m for board in boards for m in board), key=lambda m: m["start"])
    return day_speech(BY_CODE[league].name, games, datetime.now().astimezone()), FACE


async def _team(team: dict, focus: str) -> tuple[str, dict]:
    card = await spotlight.team_card(team)
    if not card:
        return f"Non trovo partite recenti o in programma per {team['name']}.", FACE
    if focus == "result" and card["kind"] in ("next", "today") and card.get("last"):
        card = {"kind": "result", "match": card["last"], "team": team}
    if focus == "next" and card["kind"] == "result":
        fixtures = football.upcoming(await football.team_fixtures(team["league"], team["id"]))
        if fixtures:
            card = {"kind": "next", "match": fixtures[0], "team": team}
    _desk().show("sport_match", {"kind": card["kind"], "match": card["match"], "team": team}, key=f"sport:{card['match']['id']}",
                 ttl=120, intent=True)
    return match_speech(card, team, datetime.now().astimezone()), FACE


async def recognise(text: str) -> dict:
    found = {"f1": find_f1(text), "league": find_league(text), "team": None}
    try:
        await refresh_index()
        found["team"] = find_team(text, known_teams())
    except SportsUnavailable:
        found["unavailable"] = True
    return found


async def answer(text: str) -> tuple[str, dict]:
    found = await recognise(text)
    if not (found["f1"] or found["league"] or found["team"]):
        raise LookupError("sports")
    mentioned = {"f1": found["f1"], "team": found["team"],
                 "league": {"name": found["league"].name, "sport_label": found["league"].sport_label} if found["league"] else None}
    plan = await understand.plan(text, mentioned)
    if not plan["sport"]:
        raise LookupError("sports")
    team, want = found["team"], plan["want"]
    league = team["league"] if team else found["league"].code if found["league"] else None
    try:
        if found["f1"] and not team and not found["league"]:
            return await _f1(want)
        if not league:
            raise LookupError("sports")
        if want == "standings" and not BY_CODE[league].cup:
            return await _table(league, team)
        if team and want != "day":
            return await _team(team, plan["focus"])
        if want == "day" or BY_CODE[league].cup:
            return await _day(league)
        return await _table(league, None)
    except SportsUnavailable as exc:
        return f"Non riesco a raggiungere i risultati sportivi in questo momento ({exc}).", FACE
