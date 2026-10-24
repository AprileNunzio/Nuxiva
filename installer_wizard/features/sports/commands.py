import asyncio
import re
import time
import unicodedata
from datetime import datetime

from features.sports import football, hockey, spotlight
from features.sports.catalog import BY_CODE
from features.sports.fetch import SportsUnavailable
from features.sports.prefs import prefs
from features.sports.speech import f1_speech, hockey_day_speech, hockey_table_speech, match_speech, table_speech

FACE = {"mode": "face"}
F1 = re.compile(r"\b(formula\s*(1|uno)|f1|gran\s*premio|gp|qualifiche|pole\s*position|griglia di partenza)\b")
HOCKEY = re.compile(r"\b(hockey|nhl|stanley cup|power play|disco su ghiaccio|ghiaccio)\b")
HOCKEY_LIVE = re.compile(r"\b(partit\w*|risultat\w*|classific\w*|quando|prossim\w*|stasera|stanotte|oggi|ieri|domani|punteggio|score|vint[oa]|perso|finit\w*|andat\w*|gioca\w*|giocato|sta giocando|diretta|live|gol|goal)\b")
HOCKEY_HISTORY = re.compile(r"\b(stanley cup|storia|record|albo|giocatore|giocatori|marcator\w*|stagione scorsa|anno scorso|anni|regole|regolamento|come si gioca|allenatore|draft)\b")
F1_TABLE = re.compile(r"\bclassific\w*\b|\bmondiale\b|\bpiloti\b|\bcostruttori\b")
FOOTBALL = re.compile(r"\b(partit\w*|risultat\w*|vint[oa]|perso|pareggi\w*|gioca\w*|giocato|segnat\w*|gol|goal|"
                      r"classific\w*|calcio|campionato|finit\w*|andat\w*|prossim\w*|incontro|derby|match|score)\b")
TABLE = re.compile(r"\bclassific\w*\b|\bstanding\w*\b")
NEXT = re.compile(r"\bprossim\w*|quando gioca\w*|gioca\w* (oggi|domani|stasera)|a che ora")
PAST = re.compile(r"\b(andat\w*|finit\w*|vint[oa]|perso|pareggiat\w*|risultat\w*|ha fatto)\b")
NAME_LEAGUES = ("ita.1", "ita.2", "eng.1", "esp.1", "ger.1", "fra.1")
ALIASES = {"juve": "juventus", "inter": "internazionale", "milan": "ac milan", "roma": "as roma", "barca": "barcelona",
           "real": "real madrid", "psg": "paris saint-germain", "bayern": "bayern munich", "atletico": "atletico madrid"}
LEAGUE_WORDS = {"serie a": "ita.1", "serie b": "ita.2", "premier": "eng.1", "liga": "esp.1", "bundesliga": "ger.1",
                "ligue 1": "fra.1", "champions": "uefa.champions", "europa league": "uefa.europa", "eredivisie": "ned.1"}


def norm(text: str) -> str:
    flat = unicodedata.normalize("NFKD", str(text or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", flat).strip()


_INDEX: dict = {"at": 0.0, "teams": []}
INDEX_EVERY = 86400


async def refresh_index() -> None:
    if time.time() - _INDEX["at"] < INDEX_EVERY and _INDEX["teams"]:
        return
    rows: list[dict] = []
    lists = await asyncio.gather(*(football.teams(code) for code in NAME_LEAGUES), return_exceptions=True)
    for code, teams in zip(NAME_LEAGUES, lists):
        if isinstance(teams, list):
            rows += [{**t, "league": code} for t in teams]
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
    for alias, target in ALIASES.items():
        words = words.replace(f" {alias} ", f" {alias} {target} ")
    best = None
    for t in teams:
        for label in {norm(t["name"]), norm(t.get("short", ""))}:
            if len(label) >= 4 and f" {label} " in words and (not best or len(label) > best[0]):
                best = (len(label), t)
    return best[1] if best else None


def find_league(text: str) -> str | None:
    flat = f" {norm(text)} "
    return next((code for word, code in LEAGUE_WORDS.items() if f" {word} " in flat), None)


def _desk():
    from features.desktop.desk import desk
    return desk


async def _f1(text: str) -> tuple[str, dict]:
    if F1_TABLE.search(text):
        card = await spotlight.f1_standings_card()
    else:
        card = await spotlight.f1_card() or await spotlight.f1_standings_card()
    _desk().show("f1_race", card, key="sport:f1", ttl=120, intent=True)
    return f1_speech(card), FACE


async def _table(league: str, team: dict | None) -> tuple[str, dict]:
    card = await spotlight.standings_card(league, {team["id"]} if team else set())
    _desk().show("sport_table", card, key=f"sport:table:{league}", ttl=120, intent=True)
    return table_speech(card, team), FACE


async def _team(team: dict, text: str) -> tuple[str, dict]:
    card = await spotlight.team_card(team)
    if not card:
        return f"Non trovo partite recenti o in programma per {team['name']}.", FACE
    wants_next = NEXT.search(text)
    if PAST.search(text) and not wants_next and card["kind"] in ("next", "today") and card.get("last"):
        card = {"kind": "result", "match": card["last"], "team": team}
    if wants_next and card["kind"] == "result":
        fixtures = football.upcoming(await football.team_fixtures(team["league"], team["id"]))
        if fixtures:
            card = {"kind": "next", "match": fixtures[0], "team": team}
    _desk().show("sport_match", {"kind": card["kind"], "match": card["match"], "team": team}, key=f"sport:{card['match']['id']}",
                 ttl=120, intent=True)
    return match_speech(card, team, datetime.now().astimezone()), FACE


async def _hockey_team(text: str, flat: str) -> tuple[str, dict] | None:
    team = find_team(flat, await hockey.teams())
    if not team:
        return None
    today, fixtures, results = await asyncio.gather(hockey.recent_games(), hockey.team_fixtures(team["id"]), hockey.team_results(team["id"]))
    mine = [m for m in today if team["id"] in (m["home"]["id"], m["away"]["id"])]
    live = next((m for m in mine if m["state"] == "in"), None)
    upcoming = football.upcoming(fixtures + [m for m in mine if m["state"] == "pre"])
    last = max((m for m in results + [m for m in mine if m["state"] == "post"]), key=lambda m: m["start"], default=None)
    wants_next = bool(NEXT.search(flat))
    if live:
        card = {"kind": "live", "match": live}
    elif wants_next and upcoming:
        card = {"kind": "next", "match": upcoming[0]}
    elif last and not (upcoming and not PAST.search(flat) and not last.get("start", "")[:10] >= datetime.now().strftime("%Y-%m-%d")):
        card = {"kind": "result", "match": last}
    elif upcoming:
        card = {"kind": "next", "match": upcoming[0]}
    elif last:
        card = {"kind": "result", "match": last}
    else:
        return f"Non trovo partite recenti o in programma per {team['name']}.", FACE
    _desk().show("sport_match", {**card, "team": team}, key=f"sport:{card['match']['id']}", ttl=120, intent=True)
    return match_speech(card, team, datetime.now().astimezone()), FACE


async def _hockey(text: str, flat: str) -> tuple[str, dict] | None:
    if TABLE.search(flat):
        team = find_team(flat, await hockey.teams())
        return hockey_table_speech(await hockey.standings(), team), FACE
    reply = await _hockey_team(text, flat)
    if reply:
        return reply
    return hockey_day_speech(await hockey.recent_games(), datetime.now().astimezone()), FACE


async def _hockey_by_team(text: str, flat: str) -> tuple[str, dict] | None:
    if not HOCKEY_LIVE.search(flat) or HOCKEY_HISTORY.search(flat):
        return None
    try:
        if find_team(flat, await hockey.teams()):
            return await _hockey_team(text, flat)
    except SportsUnavailable:
        return None
    return None


async def answer(text: str) -> tuple[str, dict]:
    flat = norm(text)
    if F1.search(flat):
        return await _f1(flat)
    try:
        if HOCKEY.search(flat) and HOCKEY_LIVE.search(flat) and not HOCKEY_HISTORY.search(flat):
            reply = await _hockey(text, flat)
            if reply:
                return reply
    except SportsUnavailable as exc:
        return f"Non riesco a raggiungere i risultati dell'hockey in questo momento ({exc}).", FACE
    if not FOOTBALL.search(flat) and not find_league(flat):
        reply = await _hockey_by_team(text, flat)
        if reply:
            return reply
        raise LookupError("sports")
    try:
        await refresh_index()
        team = find_team(flat, known_teams())
        league = find_league(flat) or (team["league"] if team else None)
        if TABLE.search(flat) and league and league in BY_CODE and not BY_CODE[league].cup:
            return await _table(league, team)
        if team:
            return await _team(team, flat)
        reply = await _hockey_by_team(text, flat)
        if reply:
            return reply
    except SportsUnavailable as exc:
        return f"Non riesco a raggiungere i risultati sportivi in questo momento ({exc}).", FACE
    raise LookupError("sports")
