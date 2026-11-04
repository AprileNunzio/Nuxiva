import json
import re
from functools import lru_cache
from pathlib import Path

from features.home_assistant.helpers import finite_number, join_words
from features.home_assistant.nlu.text import norm, phrase_stems

_UNITS = {"power": {"w", "kw", "mw"}, "energy": {"wh", "kwh", "mwh"}}
_SOLAR = re.compile(r"\b(fotovoltaic\w*|solar\w*|pannell\w*|pv|inverter|production|produzion\w*)\b")
_GENERIC = set(phrase_stems("quanta quanto quanti quale qual quali che e sta stanno ha hai stanno facendo "
                          "consumando consuma consumano consumato consumo consumi consumata consumata assorbe "
                          "assorbendo producendo produce producono prodotto prodotta produzione generando genera "
                          "energia elettrica elettrico potenza watt kilowatt w kw wh kwh fotovoltaico solare "
                          "pannelli impianto pv adesso attualmente attuale corrente misura valore sensore sensori leggi dimmi sai "
                          "oggi odierno giornaliero ieri mese mensile anno annuale giorno questo questa nel "
                          "quella della del ora casa abitazione totale"))
_PERIODS = {
    "today": set(phrase_stems("oggi odierno odierna giornaliero giornaliera daily today")),
    "yesterday": set(phrase_stems("ieri yesterday")),
    "month": set(phrase_stems("mese mensile month monthly")),
    "year": set(phrase_stems("anno annuale year yearly")),
}


@lru_cache(maxsize=4)
def messages(language: str = "it") -> dict:
    language = language if language in {"it", "en", "fr", "es"} else "it"
    path = Path(__file__).with_name("language") / f"{language}.json"
    return json.loads(path.read_text(encoding="utf-8"))["readings"]


def reading_query(text: str) -> dict | None:
    if re.search(r"\b(cos e|cosa e|che cosa|definisci|spiega\w*|significa|differenza|come funziona|"
                 r"come risparmiare)\b", text):
        return None
    if not re.search(r"\b(energ\w*|consum\w*|potenza|watt|kilowatt|w|kw|wh|kwh|fotovoltaic\w*|"
                     r"assorb\w*|produc\w*|produzion\w*)\b", text):
        return None
    tokens = set(phrase_stems(text))
    period = next((p for p, words in _PERIODS.items() if tokens & words), None)
    instant = bool(re.search(r"\b(adesso|ora|attualmente|sta|stanno|potenza|watt|kilowatt|w|kw)\b", text))
    metric = "energy" if period or re.search(r"\b(wh|kwh|energia)\b", text) and not instant else "power"
    production = bool(re.search(r"\b(fotovoltaic\w*|solar\w*|pannell\w*|pv|produc\w*|produzion\w*)\b", text))
    return {"topic": "sensor_read", "metric": metric, "production": production, "period": period, "text": text}


def _entity_tokens(entity: dict) -> set:
    return {word for phrase in entity.get("names", []) for word in phrase} | \
        set(phrase_stems(f"{entity.get('name', '')} {entity['entity_id'].replace('_', ' ')}"))


def _select(catalog, query: dict) -> list[dict]:
    metric = query["metric"]
    candidates = []
    for entity in catalog.entities.values():
        attrs = entity.get("attrs") or {}
        unit = str(attrs.get("unit_of_measurement") or "").lower().replace(" ", "")
        device_class = entity.get("device_class") or attrs.get("device_class")
        if entity.get("domain") != "sensor" or unit not in _UNITS[metric] or device_class not in (None, "", metric):
            continue
        if query.get("area_ids") and entity.get("area_id") not in query["area_ids"]:
            continue
        searchable = " ".join(" ".join(p) for p in entity.get("names", [])) + " " + \
            norm(entity["entity_id"].replace("_", " ") + " " + entity.get("name", ""))
        solar = bool(_SOLAR.search(searchable))
        if solar != query["production"]:
            continue
        if query.get("period") and not (_entity_tokens(entity) & _PERIODS[query["period"]]):
            continue
        candidates.append(entity)
    area_tokens = {word for aid in query.get("area_ids", []) for phrase in catalog.areas.get(aid, {}).get("names", [])
                   for word in phrase}
    target = set(phrase_stems(query["text"])) - _GENERIC - area_tokens
    if not target and re.search(r"\b(casa|abitazione|totale|assorb\w*|consum\w*)\b", query["text"]):
        target = set(phrase_stems("casa abitazione totale total home house potenza power consumo assorbimento"))
    if target:
        scored = [(len(target & _entity_tokens(e)), e) for e in candidates]
        best = max((score for score, _ in scored), default=0)
        candidates = [e for score, e in scored if best and score == best]
    return sorted(candidates, key=lambda e: (e.get("name", ""), e["entity_id"]))


def sensor_answer(catalog, query: dict, states: dict) -> tuple[str, dict]:
    text = messages(query.get("language", "it"))
    selected = _select(catalog, query)
    if not selected:
        return text["missing_reading"], {"mode": "face"}
    items, parts = [], []
    for entity in selected[:8]:
        state = states.get(entity["entity_id"]) or {}
        attrs = state.get("attrs") or {}
        value = finite_number(state.get("state"))
        unit = str(attrs.get("unit_of_measurement") or "")
        label = entity.get("name") or entity["entity_id"]
        device = entity.get("device_name") or ""
        if device and norm(device) not in norm(label):
            label = f"{device} · {label}"
        if value is None or unit.lower().replace(" ", "") not in _UNITS[query["metric"]]:
            shown, status = text["unavailable"], "warn"
        else:
            shown, status = f"{value:g} {unit}", ""
        parts.append(f"{label}: {shown}")
        items.append({"label": label, "value": shown, "status": status, "entity_id": entity["entity_id"]})
    prefix = text["multiple"] + " " if len(selected) > 1 else ""
    return prefix + "; ".join(parts) + ".", {
        "mode": "focus", "title": text[query["metric"]], "subtitle": text["sensor_values"],
        "panels": [{"type": "list", "title": text["sensors"], "items": items}]}


def climate_answer(rooms: list[dict], query: dict) -> tuple[str, dict]:
    text = messages(query.get("language", "it"))
    metrics = query.get("metrics") or ["temperature", "humidity"]
    parts, items = [], []
    for room in rooms:
        values = []
        for metric in metrics:
            value = finite_number(room.get(metric))
            if value is not None and (metric != "humidity" or 0 <= value <= 100):
                values.append(f"{text[metric]}: {value:g} {'%' if metric == 'humidity' else '°C'}")
            else:
                values.append(text[f"missing_{metric}"])
        shown = " · ".join(values)
        parts.append(f"{room['name']}: {shown}")
        items.append({"label": room["name"], "value": shown, "status": ""})
    if not parts:
        return text[f"missing_{metrics[0]}"], {"mode": "face"}
    return join_words(parts[:6]) + ".", {
        "mode": "focus" if len(rooms) > 1 else "face", "title": text["climate"], "subtitle": text["sensor_values"],
        "panels": [{"type": "list", "title": text["rooms"], "items": items}]}
