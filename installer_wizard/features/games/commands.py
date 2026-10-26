import re

from config import env_get
from features.desktop.desk import desk

CHESS_KEY = "chess_3d"
WIDGET_ID = "chess_3d"
GAME_URL = "/giochi/scacchi-3d/index.html"

OPEN_PATTERNS = re.compile(
    r"\b(apri|avvia|inizia|mostra|metti|carica|lancia|voglio giocare|facciamo una partita|giochiamo|gioca)\b.*\b(scacch\w*|chess|scacchiera)\b|"
    r"^\s*(?:nuxiva\s*,?\s*)?(?:giochiamo a scacchi|scacchi|chess|scacchi 3d|partita a scacchi)\s*$",
    re.I
)

FULLSCREEN_PATTERNS = re.compile(
    r"\b(tutto schermo|schermo intero|fullscreen|massimizza|ingrandisci)\b.*\b(scacch\w*|chess|gioc\w*)?\b|"
    r"\b(scacch\w*|chess)\b.*\b(tutto schermo|schermo intero|fullscreen)\b",
    re.I
)

CLOSE_PATTERNS = re.compile(
    r"\b(chiudi|esci|termina|nascondi|spegni|basta con|stop)\b.*\b(scacch\w*|chess|partita|gioc\w*)\b",
    re.I
)

RESET_PATTERNS = re.compile(
    r"\b(nuova partita|ricomincia|azzera|resetta|riavvia)\b.*\b(scacch\w*|chess|partita)?\b",
    re.I
)

HINT_PATTERNS = re.compile(
    r"\b(consigli\w*|suggerisc\w*|che mossa|aiut\w*|suggerimento|migliore mossa)\b",
    re.I
)


def enabled() -> bool:
    return env_get("NUXIVA_GAMES", "1") != "0"


def is_open() -> bool:
    return any(inst.get("key") == CHESS_KEY or inst.get("id") == WIDGET_ID for inst in desk.active())


def open_chess(fullscreen: bool = True) -> None:
    desk.scan()
    desk.show(
        WIDGET_ID,
        {"game": "scacchi-3d", "url": GAME_URL, "status": "active"},
        key=CHESS_KEY,
        priority=95,
        intent=False,
        fullscreen=fullscreen
    )


def close_chess() -> bool:
    was_open = is_open()
    desk.hide(key=CHESS_KEY)
    return was_open


async def answer(text: str) -> tuple[str, dict]:
    if not enabled():
        raise LookupError("Games feature disabled")

    cleaned = re.sub(r"\s+", " ", text.strip().lower())

    if CLOSE_PATTERNS.search(cleaned):
        closed = close_chess()
        reply = "Ho chiuso la scacchiera 3D, signore." if closed else "La scacchiera non era aperta."
        return reply, {"mode": "face", "presence": "normal"}

    if FULLSCREEN_PATTERNS.search(cleaned) and (is_open() or "scacch" in cleaned or "chess" in cleaned):
        open_chess(fullscreen=True)
        return "Scacchi 3D a tutto schermo attivati.", {
            "mode": "face",
            "presence": "mini",
            "app": "chess_3d",
            "fullscreen": True
        }

    if RESET_PATTERNS.search(cleaned) and (is_open() or "scacch" in cleaned or "chess" in cleaned):
        open_chess(fullscreen=True)
        return "Nuova partita impostata sulla scacchiera 3D. A Lei la prima mossa, signore.", {
            "mode": "face",
            "presence": "mini",
            "app": "chess_3d",
            "fullscreen": True
        }

    if HINT_PATTERNS.search(cleaned) and (is_open() or "scacch" in cleaned or "chess" in cleaned):
        return (
            "Le consiglio di controllare le quattro case centrali (e4, d4, e5, d5) e sviluppare i cavalli prima degli alfieri.",
            {"mode": "face", "presence": "mini", "app": "chess_3d", "fullscreen": True}
        )

    if OPEN_PATTERNS.search(cleaned) or "scacchi" in cleaned or "chess" in cleaned:
        open_chess(fullscreen=True)
        return (
            "Scacchiera 3D impostata come sfondo. Ho ridotto la mia presenza per lasciarle la visuale: a Lei la prima mossa, signore.",
            {"mode": "face", "presence": "mini", "app": "chess_3d", "fullscreen": True}
        )

    raise LookupError("Not a games command")
