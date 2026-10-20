import re

from features.models3d import library, parts as ops, studio

NUM = r"(?P<n>\d+(?:[.,]\d+)?)"
UNIT = r"(?:\s*(?P<u>mm|millimetr\w*|cm|centimetr\w*|metr\w*|m)\b)?"
COLOR_NAMES = "|".join(sorted(ops.COLORS, key=len, reverse=True))
SHAPE_NAMES = "|".join(sorted(ops.SHAPE_WORDS, key=len, reverse=True))
DIRECTIONS = {"destra": ("x", 1), "sinistra": ("x", -1), "alto": ("y", 1), "su": ("y", 1), "basso": ("y", -1), "giu": ("y", -1),
              "avanti": ("z", 1), "indietro": ("z", -1)}
DIMENSIONS = {"larghezza": "x", "altezza": "y", "profondita": "z", "lunghezza": "z", "spessore": "z"}
SIZE_WORDS = {"alto": "y", "alta": "y", "largo": "x", "larga": "x", "lungo": "z", "lunga": "z", "profondo": "z", "profonda": "z"}

MOVE = re.compile(r"\b(?:sposta|muovi|porta|spingi)\s+(?P<who>.+?)\s+(?:a|verso|in)\s+(?:la\s+)?(?P<dir>destra|sinistra|alto|basso|avanti|indietro)"
                  rf"(?:\s+di\s+{NUM}{UNIT})?$")
LIFT = re.compile(rf"\b(?P<verb>alza|abbassa|solleva|avvicina|allontana)\s+(?P<who>.+?)(?:\s+di\s+{NUM}{UNIT})?$")
RESIZE = re.compile(r"\b(?P<verb>ingrandisci|rimpicciolisci|riduci|allarga|restringi|allunga|accorcia|raddoppia|dimezza|aumenta|ingrossa|assottiglia)"
                    rf"\s+(?P<who>.+?)(?:\s+(?:del|di)\s+{NUM}\s*(?:%|per\s*cento))?$")
DIM = re.compile(rf"\b(?:imposta|metti|porta|rendi|fai)\s+(?:la\s+|l\s+|lo\s+)?(?P<dim>larghezza|altezza|profondita|lunghezza|spessore)\s+"
                 rf"(?:di|del|della|dello|dei)\s+(?P<who>.+?)\s+(?:a|di|da)\s+{NUM}{UNIT}$")
COLOR = re.compile(rf"\b(?:colora|dipingi|tinteggia|rendi|fai)\s+(?P<who>.+?)\s+(?:di\s+|in\s+|color\s+)?(?P<c>{COLOR_NAMES})$")
ADD = re.compile(rf"\b(?:aggiungi|inserisci|metti|crea|unisci)\s+(?:un|una|uno|un')?\s*(?P<shape>{SHAPE_NAMES})(?:\s+(?P<c>{COLOR_NAMES}))?"
                 rf"(?:\s+(?:grande|lungo|alto|di)\s+{NUM}{UNIT})?$")
REMOVE = re.compile(r"\b(?:elimina|rimuovi|togli|cancella)\s+(?P<who>.+)$")
DUPLICATE = re.compile(r"\b(?:duplica|clona|copia)\s+(?P<who>.+)$")
ROTATE = re.compile(rf"\b(?:ruota|gira|inclina)\s+(?P<who>.+?)\s+di\s+{NUM}\s*gradi(?:\s+(?:sull\s*asse|attorno\s+all\s*asse|su|lungo)\s*(?P<axis>[xyz]))?$")
SELECT = re.compile(r"\b(?:seleziona|scegli|indica|evidenzia)\s+(?P<who>.+)$")
ASK = re.compile(r"\bquant[oa]\s+(?:e|sono|misura)\s+(?P<what>alto|alta|largo|larga|lungo|lunga|profondo|profonda|grande|grosso)(?:\s+(?P<who>.+))?$")
MEASURE = re.compile(r"\b(?:misure|dimensioni|quanto\s+misura)\b(?:\s+(?:di|del|della|dello)\s+(?P<who>.+))?$")
UNDO = re.compile(r"\b(?:annulla|torna\s+indietro|disfai|undo)\b")
REDO = re.compile(r"\b(?:ripristina|rifai|ripeti|redo)\b")
GROUND = re.compile(r"\b(?:appoggia|poggia|metti)\b.*\b(?:a\s+terra|sul\s+piano|a\s+livello)\b")
CLOSE = re.compile(r"\b(?:chiudi|esci\s+da|termina)\b.*\b(?:studio|modellazione|editor)\b")
OPEN = re.compile(r"\b(?:apri|avvia|entra\s+nello)\b.*\b(?:studio|editor)\b.*(?:3d|tre\s*d)|\bmodifica\s+(?:il\s+)?modello\b(?P<what>.*)")

AXIS_NAME = {"x": "larghezza", "y": "altezza", "z": "profondità"}


def _cm(n: str | None, unit: str | None, default: float) -> float:
    if n is None:
        return default
    value = float(n.replace(",", "."))
    key = (unit or "cm").lower()
    if key.startswith(("mm", "milli")):
        return value * 0.1
    if key.startswith(("cm", "centi")):
        return value
    return value * 100.0


def _fmt(values) -> str:
    return " × ".join(f"{v:g}" for v in values) + " cm"


def _target(parts: list[dict], who: str | None) -> int:
    index = ops.find(parts, who or "")
    if index is None:
        raise studio.StudioError(f"Non trovo la parte «{(who or '').strip()}»")
    return index


def active() -> str | None:
    mid = studio.ACTIVE["id"]
    if not mid:
        return None
    try:
        library.get(mid)
    except KeyError:
        return None
    return mid


def _factor(verb: str, n: str | None) -> tuple[float, str | None]:
    pct = float(n.replace(",", ".")) / 100 if n else None
    if verb in ("raddoppia",):
        return 2.0, None
    if verb == "dimezza":
        return 0.5, None
    grow = verb in ("ingrandisci", "allarga", "allunga", "aumenta", "ingrossa")
    amount = pct if pct else 0.2
    axis = {"allarga": "x", "restringi": "x", "allunga": "y", "accorcia": "y"}.get(verb)
    return (1 + amount) if grow else max(0.05, 1 - amount), axis


def _run(mid: str, text: str) -> str | None:
    meta = library.get(mid)
    parts = meta["parts"]
    if UNDO.search(text):
        studio.undo(mid)
        return "Annullato."
    if REDO.search(text):
        studio.redo(mid)
        return "Ripristinato."
    if CLOSE.search(text):
        studio.close_studio()
        return "Studio chiuso."
    if GROUND.search(text):
        studio.operate(mid, {"op": "ground"})
        return "Ho appoggiato il modello a terra."
    if m := ADD.search(text):
        size = _cm(m.group("n"), m.group("u"), 0.0)
        color = ops.COLORS.get(m.group("c") or "", "#29e0ff")
        studio.operate(mid, {"op": "add", "shape": ops.SHAPE_WORDS[m.group("shape")], "color": color, "size": size})
        return f"Ho aggiunto {m.group('shape')}{' ' + m.group('c') if m.group('c') else ''}."
    if m := DIM.search(text):
        i = _target(parts, m.group("who"))
        value = _cm(m.group("n"), m.group("u"), 0.0)
        studio.operate(mid, {"op": "dimension", "index": i, "axis": DIMENSIONS[m.group("dim")], "value": value})
        return f"{m.group('dim').capitalize()} di {parts[i]['name']} impostata a {value:g} cm."
    if m := ROTATE.search(text):
        i = _target(parts, m.group("who"))
        axis = m.group("axis") or "y"
        studio.operate(mid, {"op": "rotate", "index": i, "axis": axis, "degrees": float(m.group("n").replace(",", "."))})
        return f"Ho ruotato {parts[i]['name']}."
    if m := COLOR.search(text):
        i = _target(parts, m.group("who"))
        studio.operate(mid, {"op": "update", "index": i, "changes": {"color": ops.COLORS[m.group("c")]}})
        return f"{parts[i]['name'].capitalize()} ora è {m.group('c')}."
    if m := MOVE.search(text):
        i = _target(parts, m.group("who"))
        axis, sign = DIRECTIONS[m.group("dir")]
        studio.operate(mid, {"op": "move", "index": i, "axis": axis, "delta": sign * _cm(m.group("n"), m.group("u"), 2.0)})
        return f"Ho spostato {parts[i]['name']}."
    if m := LIFT.search(text):
        i = _target(parts, m.group("who"))
        axis, sign = {"alza": ("y", 1), "solleva": ("y", 1), "abbassa": ("y", -1), "avvicina": ("z", 1), "allontana": ("z", -1)}[m.group("verb")]
        studio.operate(mid, {"op": "move", "index": i, "axis": axis, "delta": sign * _cm(m.group("n"), m.group("u"), 2.0)})
        return f"Ho spostato {parts[i]['name']}."
    if m := RESIZE.search(text):
        i = _target(parts, m.group("who"))
        factor, axis = _factor(m.group("verb"), m.group("n"))
        studio.operate(mid, {"op": "scale", "index": i, "factor": factor, "axis": axis})
        return f"Ho modificato {parts[i]['name']}."
    if m := DUPLICATE.search(text):
        i = _target(parts, m.group("who"))
        studio.operate(mid, {"op": "duplicate", "index": i})
        return f"Ho duplicato {parts[i]['name']}."
    if m := REMOVE.search(text):
        i = _target(parts, m.group("who"))
        name = parts[i]["name"]
        studio.operate(mid, {"op": "remove", "index": i})
        return f"Ho eliminato {name}."
    if m := SELECT.search(text):
        i = _target(parts, m.group("who"))
        studio.select(mid, i)
        return f"Ho selezionato {parts[i]['name']}."
    if m := ASK.search(text):
        size = ops.extent(parts[_target(parts, m.group("who"))]) if m.group("who") else ops.measures(parts)["overall"]["size"]
        axis = SIZE_WORDS.get(m.group("what"))
        if axis:
            return f"{AXIS_NAME[axis].capitalize()}: {size['xyz'.index(axis)]:g} cm."
        return f"Misura {_fmt(size)} (larghezza, altezza, profondità)."
    if m := MEASURE.search(text):
        if m.group("who"):
            i = _target(parts, m.group("who"))
            return f"{parts[i]['name'].capitalize()} misura {_fmt(ops.extent(parts[i]))}."
        return f"Il modello misura {_fmt(ops.measures(parts)['overall']['size'])} (larghezza, altezza, profondità)."
    return None


def answer(text: str) -> tuple[str, dict]:
    open_match = OPEN.search(ops.norm(text))
    if open_match and not active():
        what = (open_match.groupdict().get("what") or "").strip()
        meta = (library.find(what) if what else None) or next((m for m in library.listing() if m.get("parts")), None)
        if not meta:
            return "Non ho modelli da modificare: chiedimi di crearne uno, per esempio «creami un martello in 3D».", {"mode": "face"}
        studio.open_studio(meta["id"])
        return f"Studio 3D aperto su {meta['title']}.", {"mode": "face"}
    mid = active()
    if not mid:
        raise LookupError("studio")
    try:
        reply = _run(mid, ops.norm(text))
    except (studio.StudioError, ops.PartError) as exc:
        return str(exc), {"mode": "face"}
    if reply is None:
        raise LookupError("studio")
    return reply, {"mode": "face"}
