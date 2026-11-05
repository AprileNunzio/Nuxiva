import json
import os
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

MAX_OPS = 4096
MAX_DEPTH = 32
CACHE_SIZE = 16


def _native() -> Callable[[str, str], str | None] | None:
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "display_diff", None)


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _same(a, b) -> bool:
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(map(_same, a, b))
    return a == b


def _walk(old, new, path: str, depth: int, ops: list) -> None:
    if len(ops) > MAX_OPS:
        return
    if isinstance(old, dict) and isinstance(new, dict) and depth < MAX_DEPTH:
        for key in old:
            if key not in new:
                ops.append({"op": "remove", "path": f"{path}/{_escape(key)}"})
        for key, value in new.items():
            child = f"{path}/{_escape(key)}"
            if key in old:
                _walk(old[key], value, child, depth + 1, ops)
            else:
                ops.append({"op": "add", "path": child, "value": value})
        return
    if not _same(old, new):
        ops.append({"op": "replace", "path": path, "value": new})


def python_diff(old_text: str, new_text: str) -> str | None:
    ops: list = []
    _walk(json.loads(old_text), json.loads(new_text), "", 0, ops)
    return None if len(ops) > MAX_OPS else json.dumps(ops, ensure_ascii=False, separators=(",", ":"))


NATIVE = _native()
ENGINE = "rust" if NATIVE is not None else "python"


@dataclass(frozen=True)
class Build:
    number: int
    text: str


class DeltaCache:

    def __init__(self, differ: Callable[[str, str], str | None] | None = None) -> None:
        self._differ = differ or NATIVE or python_diff
        self._cache: OrderedDict[tuple[int, int], str | None] = OrderedDict()

    def ops(self, before: Build, after: Build) -> str | None:
        key = (before.number, after.number)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        result = self._differ(before.text, after.text)
        self._cache[key] = result
        while len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return result


def full_frame(build: Build, events: list[dict]) -> str:
    return f'{{"t":"full","v":{build.number},"s":{build.text}{_events(events)}}}'


def patch_frame(before: Build, after: Build, ops: str, events: list[dict]) -> str:
    return f'{{"t":"patch","f":{before.number},"v":{after.number},"p":{ops}{_events(events)}}}'


def _events(events: list[dict]) -> str:
    return f',"e":{json.dumps(events, ensure_ascii=False, default=str)}' if events else ""


def frame(cache: DeltaCache, before: Build | None, after: Build, events: list[dict]) -> str | None:
    if before is None:
        return full_frame(after, events)
    if before.number == after.number:
        return patch_frame(before, after, "[]", events) if events else None
    ops = cache.ops(before, after)
    if ops is None or len(ops) >= len(after.text):
        return full_frame(after, events)
    if ops == "[]" and not events:
        return None
    return patch_frame(before, after, ops, events)
