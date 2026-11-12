import random

from agenti.agency.text import clean, slug

MAX_ENTITIES = 40
MAX_RELATIONS = 200
MAX_ACTORS = 24
MAX_EVENTS = 32
MAX_FOLLOWS = 6
WORK = 960_000
PERSONA = 600
NAME = 120
LABEL = 60


def _line(value, limit: int, fallback: str = "") -> str:
    text = " ".join(clean(value, limit * 2).split())[:limit].strip()
    return text or fallback


def _number(value, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in (float("inf"), float("-inf")):
        return default
    return round(min(high, max(low, number)), 4)


def _items(raw, key: str, limit: int) -> list[dict]:
    values = raw.get(key) if isinstance(raw, dict) else None
    return [v for v in values if isinstance(v, dict)][:limit] if isinstance(values, list) else []


def _unique(base: str, taken: set[str]) -> str:
    candidate, counter = base, 2
    while candidate in taken:
        candidate = f"{base[:58]}-{counter}"
        counter += 1
    taken.add(candidate)
    return candidate


def _entities(raw) -> tuple[list[dict], dict[str, str]]:
    out, aliases, taken = [], {}, set()
    for item in _items(raw, "entities", MAX_ENTITIES):
        name = _line(item.get("name"), NAME)
        if not name:
            continue
        key = _unique(slug(item.get("key") or name, 48, "entity"), taken)
        aliases[slug(item.get("key") or name, 48, "entity")] = key
        aliases[slug(name, 48, "entity")] = key
        out.append({"key": key, "name": name, "kind": _line(item.get("kind"), LABEL, "entity")})
    return out, aliases


def _relations(raw, aliases: dict[str, str]) -> list[dict]:
    out, seen = [], set()
    for item in _items(raw, "relations", MAX_RELATIONS):
        a = aliases.get(slug(item.get("from"), 48, ""))
        b = aliases.get(slug(item.get("to"), 48, ""))
        if not a or not b or a == b or frozenset((a, b)) in seen:
            continue
        seen.add(frozenset((a, b)))
        out.append({"from": a, "to": b, "kind": _line(item.get("kind"), LABEL, "link"),
                    "weight": _number(item.get("weight"), -1, 1, 0)})
    return out


def _traits(item: dict, rng: random.Random, spread: float) -> dict:
    def vary(name: str, low: float, high: float, default: float) -> float:
        base = _number(item.get(name), low, high, default)
        return round(min(high, max(low, base + rng.uniform(-spread, spread))), 4)
    return {"stance": vary("stance", -1, 1, 0), "openness": vary("openness", 0, 1, 0.5),
            "activity": vary("activity", 0, 1, 0.5), "influence": vary("influence", 0, 1, 0.3),
            "stubbornness": vary("stubbornness", 0, 1, 0.3), "forum": vary("forum", 0, 1, 0.3)}


def _counts(actors: list[dict], population: int) -> list[int]:
    wanted = [max(1, int(_number(a.get("count"), 1, 2000, 1))) for a in actors]
    total = sum(wanted)
    if total <= population:
        return wanted
    scaled = [max(1, round(w * population / total)) for w in wanted]
    while sum(scaled) > population and max(scaled) > 1:
        scaled[scaled.index(max(scaled))] -= 1
    return scaled


def build(raw, question: str, population: int, rounds: int, seed: int) -> tuple[dict, dict[str, str]]:
    rng = random.Random(seed)
    entities, aliases = _entities(raw)
    actors = [a for a in _items(raw, "actors", MAX_ACTORS) if _line(a.get("name"), NAME)]
    population = max(2, min(population, WORK // max(1, rounds)))
    agents, personas, taken, leaders = [], {}, set(), []
    for actor, count in zip(actors, _counts(actors, population)):
        name = _line(actor.get("name"), NAME - 8)
        role = _line(actor.get("role"), LABEL, "person")
        entity = aliases.get(slug(actor.get("entity"), 48, ""))
        persona = _line(actor.get("persona"), PERSONA)
        base = slug(name, 40, "agent")
        for index in range(count):
            key = _unique(base if count == 1 else f"{base}-{index + 1}", taken)
            label = name if count == 1 else f"{name} {index + 1}"
            agents.append({"key": key, "name": label, "role": role, "entity": entity,
                           "traits": _traits(actor, rng, 0.0 if count == 1 else 0.15), "follows": []})
            personas[key] = persona
        if count == 1:
            leaders.append(agents[-1]["key"])
    if len(agents) < 2:
        return {}, {}
    for agent in agents:
        agent["follows"] = [k for k in rng.sample(leaders, min(len(leaders), MAX_FOLLOWS)) if k != agent["key"]]
        if agent["entity"] is None:
            agent.pop("entity")
    events = []
    for item in _items(raw, "events", MAX_EVENTS):
        event = event_spec(item, rounds, aliases, 1)
        if event:
            events.append(event)
    title = _line(raw.get("title") if isinstance(raw, dict) else "", NAME) or _line(question, NAME, "Scenario")
    scenario = {"title": title, "question": clean(question, 2000), "seed": seed, "rounds": rounds,
                "entities": entities, "relations": _relations(raw, aliases), "agents": agents, "events": events}
    return scenario, personas


def event_spec(item, rounds: int, aliases: dict[str, str], earliest: int) -> dict | None:
    if not isinstance(item, dict):
        return None
    title = _line(item.get("title"), NAME)
    try:
        round_number = int(item.get("round"))
    except (TypeError, ValueError):
        return None
    if not title or not earliest <= round_number <= rounds:
        return None
    event = {"round": round_number, "title": title, "shift": _number(item.get("shift"), -1, 1, 0),
             "reach": _number(item.get("reach"), 0, 1, 0.5)}
    target = aliases.get(slug(item.get("target"), 48, "")) if item.get("target") else None
    if target:
        event["target"] = target
    return event


def aliases_of(entities: list[dict]) -> dict[str, str]:
    out = {}
    for entity in entities:
        out[entity["key"]] = entity["key"]
        out[slug(entity["name"], 48, "entity")] = entity["key"]
    return out
