from features.musicstudio import catalog as C, genres, theory as T
from features.musicstudio.genre_model import Genre

NOTE_ROLES = ("kit", "bass_i", "chords_i", "lead_i")


def profile(item: Genre) -> str:
    gear = ", ".join(C.BY_ID[getattr(item, k)].name for k in NOTE_ROLES)
    prog = item.prog or "diatonic"
    return (f"{item.id} ({item.name}, family {item.family}): tempo {item.tempo[0]}-{item.tempo[1]} bpm, {item.beats}/4, scale {item.mode}, progression {prog}"
            f"{', swing' if item.swing else ''}{', seventh chords' if item.seventh else ''}; typical gear: {gear}; feel: {item.feel}")


def candidates(text: str, limit: int = 3) -> list[Genre]:
    return genres.search(text, limit)


def brief(text: str, limit: int = 3) -> str:
    found = candidates(text, limit)
    return "\n".join(profile(x) for x in found)


def index() -> str:
    return "; ".join(f"{family}: {', '.join(ids)}" for family, ids in genres.families().items())


def progressions() -> str:
    return ", ".join(sorted(T.NAMED))


def blend(primary: str, secondary: str) -> dict:
    first, second = genres.get(primary), genres.get(secondary)
    return {"chords": second.chords_i, "lead": second.lead_i, "pad": second.pad_i} if second.id != first.id else {}
