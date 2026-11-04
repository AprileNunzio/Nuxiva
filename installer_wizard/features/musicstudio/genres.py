from features.musicstudio import genres_classic, genres_latin, genres_pop, genres_urban, genres_world
from features.musicstudio.genre_model import Genre

ALL: tuple[Genre, ...] = genres_pop.GENRES + genres_urban.GENRES + genres_latin.GENRES + genres_world.GENRES + genres_classic.GENRES
BY_ID = {x.id: x for x in ALL}
IDS = tuple(x.id for x in ALL)
LEGACY = {"hiphop": "hiphop", "latin": "latin"}


def get(genre: str) -> Genre:
    return BY_ID.get(genre) or BY_ID["pop"]


def families() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for item in ALL:
        out.setdefault(item.family, []).append(item.id)
    return out


def search(text: str, limit: int = 5) -> list[Genre]:
    low = str(text or "").lower()
    scored = []
    for item in ALL:
        score = sum(len(t) for t in item.tags + (item.name.lower(), item.id) if t and t in low)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda s: -s[0])
    return [s[1] for s in scored[:limit]]


def public() -> list[dict]:
    return [{"id": x.id, "name": x.name, "family": x.family, "tempo": list(x.tempo), "mode": x.mode, "beats": x.beats, "tags": list(x.tags), "feel": x.feel} for x in ALL]
