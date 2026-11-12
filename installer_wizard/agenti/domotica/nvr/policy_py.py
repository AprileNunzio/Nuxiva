from agenti.nvr.index_py import tokens

MAX_EXTRA = 50
MAX_EXTRA_LEN = 64
MAX_ROOM_LEN = 200
PRIVATE_ROOMS = ("bagno", "bagni", "wc", "toilette", "doccia", "camera", "camere", "cameretta", "camerette", "stanza da letto",
                 "spogliatoio", "bathroom", "restroom", "toilet", "shower", "bedroom", "nursery", "dressing room",
                 "changing room", "salle de bain", "salle de bains", "toilettes", "chambre", "douche", "vestiaire", "bano",
                 "banos", "aseo", "dormitorio", "habitacion", "recamara", "vestidor", "ducha")


def _contains(room: list[str], phrase: str) -> bool:
    wanted = tokens(phrase)
    n = len(wanted)
    return bool(wanted) and any(room[i:i + n] == wanted for i in range(len(room) - n + 1))


def is_private_room(room: str, extra: list[str]) -> bool:
    words = tokens(room[:MAX_ROOM_LEN])
    return any(_contains(words, p) for p in PRIVATE_ROOMS) or any(
        _contains(words, e) for e in extra[:MAX_EXTRA] if len(e) <= MAX_EXTRA_LEN)


def py_audio_decision(room: str, opted_in: bool, notice_active: bool, extra: list[str]) -> tuple[bool, str, bool]:
    private = is_private_room(room, extra)
    reason = "private_room" if private else "notice_off" if not notice_active else "not_opted_in" if not opted_in else "allowed"
    return reason == "allowed", reason, private
