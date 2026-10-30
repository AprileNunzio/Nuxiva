import re
import unicodedata
from functools import lru_cache

from tasks import background

from features.agency import board, service
from features.agency.client import AgencyRejected, AgencyUnavailable
from features.agency.presence import intent
from features.agency.words import LANGUAGES, word

FACE = {"mode": "face"}
TEXT_LIMIT = 2000
ORDER = (("open", "show", "close", "status"), ("start", "build"))
ACTIVE = ("planning", "running", "waiting_user", "paused")


@lru_cache(maxsize=len(LANGUAGES) * 8)
def pattern(lang: str, key: str) -> re.Pattern:
    return re.compile(word(lang, "commands", key), re.I)


def detect(text: str) -> tuple[str, str, re.Match] | None:
    for keys in ORDER:
        for lang in LANGUAGES:
            for key in keys:
                match = pattern(lang, key).search(text)
                if match:
                    return lang, key, match
    return None


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()


def best(cards: list[dict], name: str) -> dict | None:
    words = [w for w in re.findall(r"[a-z0-9]+", _plain(name)) if len(w) > 2]
    scored = [(sum(w in _plain(c["title"]) for w in words), c) for c in cards]
    top = max(scored, key=lambda pair: pair[0], default=(0, None))
    return top[1] if top[0] > 0 else None


async def status(lang: str, cards: list[dict]) -> str:
    active = [c for c in cards if c["status"] in ACTIVE]
    if not active:
        return word(lang, "replies", "none")
    items = "; ".join(word(lang, "replies", "item").format(title=c["title"], percent=c["percent"], done=c["counts"]["done"],
                                                           total=c["counts"]["total"]) for c in active[:6])
    return word(lang, "replies", "list").format(items=items)


async def view(lang: str, key: str, match: re.Match) -> str:
    if key == "close":
        intent.push("close")
        return word(lang, "replies", "closed")
    cards = (await board.overview())["projects"]
    if key == "status":
        return await status(lang, cards)
    if key == "show":
        intent.push("galaxy")
        return word(lang, "replies", "shown")
    project = best(cards, match.group("name"))
    if project is None:
        intent.push("galaxy")
        return word(lang, "replies", "not_found")
    intent.push("project", project["id"])
    return word(lang, "replies", "opened").format(title=project["title"])


async def answer(text: str) -> tuple[str, dict]:
    if not isinstance(text, str) or len(text) > TEXT_LIMIT:
        raise LookupError("agency")
    found = detect(text)
    if found is None:
        raise LookupError("agency")
    lang, key, match = found
    if key in ("start", "build"):
        if len(text.strip()) < service.GOAL_MIN:
            return word(lang, "replies", "short"), FACE
        background(service.launch(text.strip(), lang))
        return word(lang, "replies", "started"), {**FACE, "agency": intent.push("galaxy")}
    before = intent.current()
    try:
        speech = await view(lang, key, match)
    except (AgencyUnavailable, AgencyRejected):
        return word(lang, "replies", "offline"), FACE
    after = intent.current()
    return speech, ({**FACE, "agency": after} if after and after != before else FACE)
