import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from features.sports import fetch, football, formula1
from features.sports.catalog import LIVE, POST
from features.sports.fetch import SportsUnavailable
from features.sports.prefs import prefs

log = logging.getLogger("nuxiva.sports")
NIGHT_HOUR = 3
HORIZON = 30 * 3600
RETRY = 1800
_next_try = 0.0


def _start(match: dict) -> float:
    try:
        return datetime.fromisoformat(match["start"].replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _expiry(matches: list[dict], now: float) -> float:
    limit = now + HORIZON
    for m in matches:
        if m["state"] == LIVE:
            return now
        if m["state"] != POST and _start(m) > now:
            limit = min(limit, _start(m))
    return limit


async def _league(league: str, teams: set[str], now: float) -> None:
    day = datetime.now(timezone.utc).date()
    prefixes = (football.site(league), football.core(league))
    with fetch.capture(now + HORIZON):
        boards = await asyncio.gather(*(football.scoreboard(league, d) for d in (day - timedelta(days=1), None, day + timedelta(days=1))))
        fixtures = await asyncio.gather(*(football.team_fixtures(league, t) for t in teams))
    matches = [m for board in boards[1:] for m in board] + [m for rows in fixtures for m in rows]
    until = _expiry(matches, now)
    fetch.retime(prefixes, until)
    with fetch.capture(until):
        await asyncio.gather(football.standings(league), football.teams(league), *(football.team_results(league, t) for t in teams))


async def _f1(now: float) -> None:
    with fetch.capture(now + HORIZON):
        races = await formula1.schedule()
    weekend = formula1.next_weekend(races, datetime.fromtimestamp(now, timezone.utc))
    until = now + HORIZON
    if weekend:
        if weekend["live"]:
            until = now
        elif weekend["next_session"]:
            until = min(until, datetime.fromisoformat(weekend["next_session"]["start"]).timestamp())
    fetch.retime((formula1.BASE,), until)
    with fetch.capture(until):
        await asyncio.gather(formula1.last_results(), formula1.driver_standings(), formula1.constructor_standings())


async def build() -> dict:
    followed = prefs.followed_teams()
    by_league: dict[str, set[str]] = {}
    for league, tid in followed:
        by_league.setdefault(league, set()).add(tid)
    wants_f1 = bool(prefs.f1_fans())
    if not by_league and not wants_f1:
        fetch.reset()
        return fetch.status()
    now = time.time()
    jobs = [_league(league, ids, now) for league, ids in by_league.items()]
    if wants_f1:
        jobs.append(_f1(now))
    results = await asyncio.gather(*jobs, return_exceptions=True)
    failed = [r for r in results if isinstance(r, Exception)]
    for error in failed:
        log.warning("Aggiornamento notturno sport incompleto: %s", error)
    if len(failed) == len(results):
        raise SportsUnavailable("aggiornamento notturno non riuscito")
    fetch.commit(datetime.now().astimezone().date().isoformat())
    return fetch.status()


def due(now: datetime | None = None) -> bool:
    now = now or datetime.now().astimezone()
    if not (prefs.followed_teams() or prefs.f1_fans()):
        return False
    return now.hour >= NIGHT_HOUR and fetch.built_day() != now.date().isoformat()


async def maybe_build() -> None:
    global _next_try
    if time.time() < _next_try or not due():
        return
    try:
        await build()
    except SportsUnavailable as exc:
        _next_try = time.time() + RETRY
        log.warning("%s", exc)
