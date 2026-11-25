import logging

import httpx

from config import env_get
from state import store as state_store

from agenti.hands.holo.catalog import fetch, judge, polyhaven, sketchfab
from agenti.hands.holo.catalog.store import catalog

log = logging.getLogger("nuxiva.hands.holo.catalog")
SHORTLIST = 6
MIN_MATCH = 7
NET_ERRORS = (httpx.HTTPError, fetch.FetchError, ValueError, TimeoutError, OSError, RuntimeError)
SOURCES = {"sketchfab": sketchfab, "polyhaven": polyhaven}


def enabled() -> bool:
    return env_get("NUXIVA_HOLO_CATALOG", "1") != "0"


def threshold() -> int:
    raw = env_get("NUXIVA_HOLO_MIN_SCORE", "70")
    return max(40, min(95, int(raw))) if raw.isdigit() else 70


def key_of(subject: str) -> str:
    from agenti.particles.store import concept_key
    return concept_key(subject)


def asset_scene(entry: dict) -> dict:
    asset = {k: entry.get(k) for k in ("id", "name", "author", "license", "page", "animations", "score", "source")}
    asset["url"] = f"/api/hands/display/holo/asset/{entry['id']}"
    return {"title": entry.get("name", ""), "parts": [], "layers": 1, "euler": "XYZ", "asset": asset}


async def english(subject: str) -> str:
    from agenti.locale.pivot import pivot
    try:
        return await pivot.from_pivot(subject, "en", force=True)
    except NET_ERRORS as exc:
        log.info("traduzione del soggetto non disponibile: %s", exc)
        return subject


async def _candidates(subject: str, english: str, notify) -> list[dict]:
    found = []
    if sketchfab.token():
        notify("searching", source="Sketchfab")
        try:
            found += await sketchfab.search(english or subject)
        except NET_ERRORS as exc:
            state_store.event("WARN", f"Ricerca su Sketchfab per «{subject}» non riuscita: {exc}", "holo")
    notify("searching", source="Poly Haven")
    try:
        found += await polyhaven.search(subject, english)
    except NET_ERRORS as exc:
        state_store.event("WARN", f"Ricerca su Poly Haven per «{subject}» non riuscita: {exc}", "holo")
    return found


async def _rated(subject: str, candidates: list[dict], notify) -> list[tuple[dict, dict]]:
    out = []
    shortlist = sorted(candidates, key=judge.prefilter, reverse=True)[:SHORTLIST]
    notify("rating", n=len(shortlist))
    for candidate in shortlist:
        try:
            verdict = await judge.look(candidate, subject)
        except NET_ERRORS as exc:
            log.info("miniatura di %s non valutata: %s", candidate["uid"], exc)
            continue
        if verdict["match"] >= MIN_MATCH:
            out.append((candidate, verdict))
    out.sort(key=lambda pair: pair[1]["match"] * 10 + pair[1]["quality"], reverse=True)
    return out


def cached(subject: str, notify=lambda key, **params: None) -> dict | None:
    found = catalog.best(key_of(subject))
    if found:
        notify("cached", name=found.get("name", ""))
    return found


async def find(subject: str, notify=lambda key, **params: None, english_name: str = "") -> dict | None:
    key = key_of(subject)
    hit = cached(subject, notify)
    if hit:
        return hit
    if not enabled():
        return None
    english_name = english_name or await english(subject)
    limit = threshold()
    for candidate, verdict in await _rated(subject, await _candidates(subject, english_name, notify), notify):
        notify("downloading", name=candidate["name"])
        try:
            glb = await SOURCES[candidate["source"]].download(candidate["uid"])
            report = judge.inspect(glb)
        except NET_ERRORS as exc:
            log.info("modello %s scartato: %s", candidate["uid"], exc)
            continue
        score = judge.final(report, verdict)
        if score < limit:
            notify("rejected", name=candidate["name"], score=score)
            continue
        record = {**{k: candidate[k] for k in ("source", "uid", "name", "license", "author", "page")},
                  "animations": report["animations"], "triangles": report["triangles"], "score": score,
                  "verdict": verdict, "reasons": report["reasons"]}
        entry = catalog.add(key, glb, record)
        notify("chosen", name=candidate["name"], score=score)
        state_store.event("INFO", f"Modello 3D «{candidate['name']}» di {candidate['author']} ({candidate['license']}) "
                                  f"aggiunto al catalogo per «{subject}», punteggio {score}", "holo")
        return entry
    notify("none", limit=limit)
    state_store.event("INFO", f"Nessun modello 3D pronto supera la soglia {limit} per «{subject}»", "holo")
    return None
