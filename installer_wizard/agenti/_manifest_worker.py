from ._text import has_control, trim

MAX_KIND = 32
MAX_SCOPE = 64
MAX_SCOPE_ITEM = 128
LIMITS = {
    "concurrency_max": 256,
    "tokens_max": 10_000_000,
    "tool_calls_max": 10_000,
    "time_ms": 86_400_000,
}
_I64_MIN = -(2**63)
_U64_MAX = 2**64 - 1


def _issue(field: str, code: str) -> dict:
    return {"field": field, "code": code, "severity": "error"}


def _bounded(value, maximum: int, field: str, issues: list) -> int:
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or value < _I64_MIN or value > _U64_MAX:
        issues.append(_issue(field, "type_number"))
        return 0
    if value < 0 or value > maximum:
        issues.append(_issue(field, "out_of_range"))
        return 0
    return value


def _kind(raw: dict, issues: list) -> str:
    value = raw.get("kind")
    if value is None:
        return ""
    if not isinstance(value, str):
        issues.append(_issue("worker.kind", "type_string"))
        return ""
    clean = trim(value)
    if clean and len(clean) <= MAX_KIND and all(c.isascii() and (c.islower() or c.isdigit() or c == "_") for c in clean):
        return clean
    issues.append(_issue("worker.kind", "invalid"))
    return ""


def _scope(value, issues: list) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        issues.append(_issue("worker.tools_scope", "type_list"))
        return []
    if len(value) > MAX_SCOPE:
        issues.append(_issue("worker.tools_scope", "too_many"))
        return []
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            issues.append(_issue("worker.tools_scope", "type_item"))
            continue
        clean = trim(item)
        if not clean:
            continue
        if has_control(clean) or len(clean) > MAX_SCOPE_ITEM:
            issues.append(_issue("worker.tools_scope", "invalid"))
        elif clean not in out:
            out.append(clean)
    return out


def _graph(raw: dict, issues: list) -> bool:
    value = raw.get("needs_graph")
    if value is None:
        return False
    if not isinstance(value, bool):
        issues.append(_issue("worker.needs_graph", "type_bool"))
        return False
    return value


def parse(obj: dict, issues: list) -> dict | None:
    raw = obj.get("worker")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        issues.append(_issue("worker", "type_object"))
        return None
    block = {"kind": _kind(raw, issues)}
    for key, maximum in LIMITS.items():
        block[key] = _bounded(raw.get(key), maximum, f"worker.{key}", issues)
    block["tools_scope"] = _scope(raw.get("tools_scope"), issues)
    block["needs_graph"] = _graph(raw, issues)
    return block
