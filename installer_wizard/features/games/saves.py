import re
import secrets
import threading
import time

from config import STATE_DIR
from features.people import people
from features.people.private_store import KEY_FILE
from sealed import SealedFile

FOLDER = STATE_DIR / "games"
MAX_SAVES = 20
MAX_MOVES = 600
COLORS = ("white", "black")
PROMOTIONS = ("", "queen", "rook", "bishop", "knight")
SAVE_ID = re.compile(r"^[a-f0-9]{12}$")
_lock = threading.Lock()


def _file(slug: str) -> SealedFile:
    FOLDER.mkdir(parents=True, exist_ok=True)
    return SealedFile(FOLDER / f"{people.slugify(slug)}.chess", KEY_FILE)


def clean(save: object) -> dict:
    if not isinstance(save, dict) or save.get("v") != 1 or save.get("player") not in COLORS:
        raise ValueError("Partita non valida")
    moves = save.get("moves")
    if not isinstance(moves, list) or len(moves) > MAX_MOVES:
        raise ValueError("Partita non valida")
    out = []
    for move in moves:
        if not isinstance(move, list) or len(move) != 5:
            raise ValueError("Partita non valida")
        coords = move[:4]
        if not all(isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 7 for n in coords) or move[4] not in PROMOTIONS:
            raise ValueError("Partita non valida")
        out.append([*coords, move[4]])
    return {"v": 1, "moves": out, "player": save["player"]}


def summary(row: dict) -> dict:
    return {k: row[k] for k in ("id", "created", "updated", "moves", "turn", "over", "winner", "player")}


def listing(slug: str) -> list[dict]:
    rows = _file(slug).load().get("saves", [])
    return sorted((summary(r) for r in rows), key=lambda r: -r["updated"])


def get(slug: str, save_id: str) -> dict | None:
    return next((r for r in _file(slug).load().get("saves", []) if r["id"] == save_id), None)


def put(slug: str, save_id: str, body: dict, now: float | None = None) -> dict:
    now = now or time.time()
    save = clean(body.get("save"))
    turn = "black" if len(save["moves"]) % 2 else "white"
    winner = body.get("winner") if body.get("winner") in COLORS else None
    with _lock:
        sealed = _file(slug)
        rows = [r for r in sealed.load().get("saves", [])]
        row = next((r for r in rows if r["id"] == save_id), None)
        if row is None:
            if save_id != "new" and not SAVE_ID.match(save_id):
                raise ValueError("Partita non trovata")
            row = {"id": secrets.token_hex(6), "created": now}
            rows.append(row)
        row.update(updated=now, moves=len(save["moves"]), turn=turn, over=bool(body.get("over")), winner=winner,
                   player=save["player"], save=save)
        rows.sort(key=lambda r: -r["updated"])
        sealed.save({"saves": rows[:MAX_SAVES]})
    return summary(row)


def remove(slug: str, save_id: str) -> bool:
    with _lock:
        sealed = _file(slug)
        rows = sealed.load().get("saves", [])
        kept = [r for r in rows if r["id"] != save_id]
        if len(kept) == len(rows):
            return False
        sealed.save({"saves": kept})
    return True


def forget(slug: str) -> None:
    target = FOLDER / f"{people.slugify(slug)}.chess"
    if target.exists():
        target.unlink()
