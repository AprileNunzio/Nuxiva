import copy
import threading

from features.desktop.desk import desk
from features.models3d import generator, library, parts as ops

WIDGET = "studio_3d"
HISTORY = 40
_lock = threading.RLock()
_selected: dict[str, int | None] = {}
ACTIVE: dict[str, str | None] = {"id": None}


class StudioError(ValueError):
    pass


def key(mid: str) -> str:
    return f"studio:{mid}"


def state(meta: dict) -> dict:
    parts = meta.get("parts", [])
    chosen = _selected.get(meta["id"])
    return {"id": meta["id"], "title": meta["title"], "rev": meta.get("rev", 0), "parts": parts, "measures": ops.measures(parts),
            "selected": chosen if chosen is not None and chosen < len(parts) else None,
            "can_undo": bool(meta.get("undo")), "can_redo": bool(meta.get("redo")), "shapes": sorted(ops.DEFAULTS),
            "colors": ops.COLORS, "url": f"/api/models3d/{meta['id']}/", "main": meta.get("main", ""), "files": [f["name"] for f in meta.get("files", [])]}


def publish(meta: dict) -> dict:
    data = state(meta)
    if ACTIVE["id"] == meta["id"]:
        desk.show(WIDGET, data, key=key(meta["id"]), ttl=3600)
    return data


def open_studio(mid: str, speak: str = "") -> dict:
    meta = library.get(mid)
    if not meta.get("parts"):
        raise StudioError("Questo modello non è modificabile: non è stato creato da Nuxiva")
    with _lock:
        if ACTIVE["id"] and ACTIVE["id"] != mid:
            desk.hide(key=key(ACTIVE["id"]))
        ACTIVE["id"] = mid
    desk.hide("viewer_3d")
    data = state(meta)
    payload = {**data, **({"announce": True, "speak": speak} if speak else {})}
    desk.show(WIDGET, payload, key=key(mid), ttl=3600)
    return data


def close_studio() -> None:
    with _lock:
        mid, ACTIVE["id"] = ACTIVE["id"], None
    if mid:
        desk.hide(key=key(mid))


def _commit(meta: dict, parts: list[dict]) -> dict:
    meta["undo"] = (meta.get("undo") or [])[-(HISTORY - 1):] + [meta["parts"]]
    meta["redo"] = []
    meta["parts"] = parts
    meta["rev"] = meta.get("rev", 0) + 1
    return publish(generator.render(meta))


def edit(mid: str, change) -> dict:
    with _lock:
        meta = library.get(mid)
        before = meta.get("parts")
        if not before:
            raise StudioError("Questo modello non è modificabile")
        parts = copy.deepcopy(before)
        try:
            change(parts)
        except ops.PartError as exc:
            raise StudioError(str(exc))
        if parts == before:
            return state(meta)
        return _commit(meta, parts)


def select(mid: str, index: int | None) -> dict:
    with _lock:
        meta = library.get(mid)
        _selected[mid] = index if index is not None and 0 <= index < len(meta.get("parts", [])) else None
        return publish(meta)


def _step(mid: str, source: str, target: str) -> dict:
    with _lock:
        meta = library.get(mid)
        stack = meta.get(source) or []
        if not stack:
            raise StudioError("Niente da annullare" if source == "undo" else "Niente da ripristinare")
        meta[target] = (meta.get(target) or [])[-(HISTORY - 1):] + [meta["parts"]]
        meta["parts"] = stack.pop()
        meta[source] = stack
        meta["rev"] = meta.get("rev", 0) + 1
        return publish(generator.render(meta))


def undo(mid: str) -> dict:
    return _step(mid, "undo", "redo")


def redo(mid: str) -> dict:
    return _step(mid, "redo", "undo")


def _index(parts: list[dict], index) -> int:
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(parts):
        raise ops.PartError("Parte inesistente")
    return index


def operate(mid: str, body: dict) -> dict:
    name = body.get("op")
    if name == "undo":
        return undo(mid)
    if name == "redo":
        return redo(mid)
    if name == "select":
        return select(mid, body.get("index"))

    def change(parts: list[dict]) -> None:
        if name == "add":
            parts.append(ops.fresh(parts, str(body.get("shape")), str(body.get("color") or "#29e0ff"), str(body.get("name") or ""),
                                   float(body.get("size") or 0)))
            _selected[mid] = len(parts) - 1
            return
        if name == "ground":
            ops.ground(parts)
            return
        i = _index(parts, body.get("index"))
        part = parts[i]
        if name == "remove":
            parts.pop(i)
            _selected[mid] = None
        elif name == "duplicate":
            copy_ = copy.deepcopy(part)
            copy_["name"] = ops.unique_name(parts, part["name"])
            ops.translate(copy_, "x", ops.extent(part)[0] + 1)
            parts.append(ops.clean(copy_))
            _selected[mid] = len(parts) - 1
        elif name == "update":
            changes = body.get("changes")
            if not isinstance(changes, dict):
                raise ops.PartError("Modifiche non valide")
            parts[i] = ops.clean({**part, **{k: v for k, v in changes.items() if k in ops.KEYS and k != "shape"}})
        elif name == "move":
            ops.translate(part, _axis(body), float(body.get("delta") or 0))
        elif name == "rotate":
            ops.rotate(part, _axis(body), float(body.get("degrees") or 0))
        elif name == "scale":
            ops.scale_by(part, float(body.get("factor") or 1), body.get("axis") if body.get("axis") in ops.AXES else None)
        elif name == "transform":
            factor, degrees = float(body.get("factor") or 1), float(body.get("degrees") or 0)
            delta = ops.vector(body.get("delta") or [0, 0, 0])
            if factor != 1:
                ops.scale_by(part, factor)
            if degrees:
                ops.rotate(part, "y", degrees)
            for axis, value in zip(ops.AXES, delta):
                if value:
                    ops.translate(part, axis, value)
        elif name == "dimension":
            ops.set_dimension(part, _axis(body), float(body.get("value") or 0))
        else:
            raise ops.PartError("Operazione sconosciuta")

    return edit(mid, change)


def _axis(body: dict) -> str:
    if body.get("axis") not in ops.AXES:
        raise ops.PartError("Asse non valido")
    return body["axis"]
