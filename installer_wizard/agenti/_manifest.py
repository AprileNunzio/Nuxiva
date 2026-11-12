import json
import math
import re

from ._text import has_control, trim

MAX_MANIFEST_BYTES = 64 * 1024
MAX_ID = 40
MAX_NAME = 80
MAX_DESCRIPTION = 1_200
MAX_ITEM = 400
MAX_LIST = 64
MAX_ROUTING = 160
MAX_RAM_MB = 1_048_576

CATEGORIES = (
    "creativita", "percezione", "cognizione", "sicurezza", "domotica", "infrastruttura", "multimedia",
    "comunicazione", "conoscenza", "salute", "sport", "scienza", "informatica",
)
LEGACY_CATEGORIES = ("assistente", "casa", "home", "intrattenimento", "intelligenza", "sistema", "altro")
RESERVED_IDS = ("agenti", "features", "registry", "loader", "schema", "scaffold", "core", "category")
_ID = re.compile(r"[a-z][a-z0-9_]{1,39}")
_FOLDER = re.compile(r"[a-z0-9][a-z0-9_-]{1,40}")
_MISSING = object()


def valid_id(value: str) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def valid_folder(value: str) -> bool:
    return isinstance(value, str) and _FOLDER.fullmatch(value) is not None


def _issue(field: str, code: str, severity: str = "error") -> dict:
    return {"field": field, "code": code, "severity": severity}


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _text(obj: dict, key: str, limit: int, issues: list) -> str:
    value = obj.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        issues.append(_issue(key, "type_string"))
        return ""
    clean = trim(value)
    if has_control(clean):
        issues.append(_issue(key, "control_chars"))
        return ""
    if len(clean) > limit:
        issues.append(_issue(key, "too_long"))
        return ""
    return clean


def _item(value):
    if isinstance(value, str):
        return trim(value)
    if isinstance(value, dict):
        raw = value["name"] if "name" in value else value.get("id")
        return trim(raw) if isinstance(raw, str) else None
    return None


def _list(value, field: str, limit: int, issues: list) -> list[str]:
    if value is _MISSING or value is None:
        return []
    if not isinstance(value, list):
        issues.append(_issue(field, "type_list"))
        return []
    if len(value) > limit:
        issues.append(_issue(field, "too_many"))
        return []
    out: list[str] = []
    for raw in value:
        item = _item(raw)
        if item is None:
            issues.append(_issue(field, "type_item"))
            continue
        if not item:
            continue
        if has_control(item):
            issues.append(_issue(field, "control_chars"))
        elif len(item) > MAX_ITEM:
            issues.append(_issue(field, "too_long"))
        elif item not in out:
            out.append(item)
    return out


def _megabytes(value, scale: float, field: str, issues: list) -> int:
    if value is _MISSING or value is None:
        return 0
    if not _is_number(value):
        issues.append(_issue(field, "type_number"))
        return 0
    try:
        scaled = float(value) * scale
    except OverflowError:
        scaled = math.inf
    if not math.isfinite(scaled) or scaled < 0.0 or scaled > 1_048_576.0:
        issues.append(_issue(field, "out_of_range"))
        return 0
    return min(int(f"{scaled:.0f}"), MAX_RAM_MB)


def _profile(obj: dict, issues: list) -> dict:
    raw = obj.get("profile")
    if raw is not None:
        if not isinstance(raw, dict):
            issues.append(_issue("profile", "type_object"))
            return {"ram_mb": 0, "vram_mb": 0, "heavy": False}
        heavy = raw.get("heavy")
        if heavy is None:
            heavy = False
        elif not isinstance(heavy, bool):
            issues.append(_issue("profile.heavy", "type_bool"))
            heavy = False
        return {
            "ram_mb": _megabytes(raw.get("ram_mb", _MISSING), 1.0, "profile.ram_mb", issues),
            "vram_mb": _megabytes(raw.get("vram_mb", _MISSING), 1.0, "profile.vram_mb", issues),
            "heavy": heavy,
        }
    req = obj.get("requires")
    if not isinstance(req, dict):
        return {"ram_mb": 0, "vram_mb": 0, "heavy": False}
    return {
        "ram_mb": _megabytes(req.get("ram_gb", _MISSING), 1024.0, "requires.ram_gb", issues),
        "vram_mb": _megabytes(req.get("gpu_vram_gb", _MISSING), 1024.0, "requires.gpu_vram_gb", issues),
        "heavy": False,
    }


def _routing(obj: dict, issues: list) -> dict:
    raw = obj.get("routing")
    if raw is None:
        return {"nouns": [], "phrases": [], "verbs": []}
    if not isinstance(raw, dict):
        issues.append(_issue("routing", "type_object"))
        return {"nouns": [], "phrases": [], "verbs": []}
    return {
        key: _list(raw.get(key, _MISSING), f"routing.{key}", MAX_ROUTING, issues)
        for key in ("nouns", "phrases", "verbs")
    }


def _identity(obj: dict, folder: str, issues: list) -> str:
    raw = obj.get("id")
    if raw is None:
        ident = folder
    elif isinstance(raw, str):
        ident = trim(raw)
    else:
        issues.append(_issue("id", "type_string"))
        return ""
    if not valid_id(ident):
        issues.append(_issue("id", "id_invalid"))
    elif ident in RESERVED_IDS:
        issues.append(_issue("id", "id_reserved"))
    elif folder and ident != folder:
        issues.append(_issue("id", "id_folder_mismatch", "warning"))
    return ident


def _category(obj: dict, physical: str | None, issues: list) -> str:
    declared = _text(obj, "category", 40, issues)
    if physical is not None:
        if declared in CATEGORIES and declared != physical:
            issues.append(_issue("category", "category_folder_mismatch", "warning"))
        if physical not in CATEGORIES:
            issues.append(_issue("category", "category_unknown", "warning"))
        return physical
    if not declared:
        issues.append(_issue("category", "category_missing", "warning"))
        return "altro"
    if declared not in CATEGORIES:
        code = "category_legacy" if declared in LEGACY_CATEGORIES else "category_unknown"
        issues.append(_issue("category", code, "warning"))
    return declared


def validate_value(raw, folder: str, physical: str | None = None) -> dict:
    if not isinstance(raw, dict):
        return {"manifest": None, "issues": [_issue("", "not_object")]}
    issues: list[dict] = []
    ident = _identity(raw, folder, issues)
    name = _text(raw, "name", MAX_NAME, issues)
    if not name:
        issues.append(_issue("name", "name_missing"))
    manifest = {"id": ident, "name": name}
    manifest["icon"] = _text(raw, "icon", 16, issues)
    manifest["category"] = _category(raw, physical, issues)
    manifest["description"] = _text(raw, "description", MAX_DESCRIPTION, issues)
    manifest["capabilities"] = _list(raw.get("capabilities", _MISSING), "capabilities", MAX_LIST, issues)
    manifest["routing"] = _routing(raw, issues)
    manifest["profile"] = _profile(raw, issues)
    for key in ("tools", "skills", "widgets"):
        manifest[key] = _list(raw.get(key, _MISSING), key, MAX_LIST, issues)
    manifest["api"] = _text(raw, "api", 64, issues)
    manifest["source"] = _text(raw, "source", 16, issues)
    manifest["version"] = _text(raw, "version", 32, issues)
    if not manifest["description"]:
        issues.append(_issue("description", "description_missing", "warning"))
    failed = any(i["severity"] == "error" for i in issues)
    return {"manifest": None if failed else manifest, "issues": issues}


def _reject_constant(token: str):
    raise ValueError(token)


def validate(raw: str, folder: str, physical: str | None = None) -> dict:
    if len(raw.encode("utf-8")) > MAX_MANIFEST_BYTES:
        return {"manifest": None, "issues": [_issue("", "too_large")]}
    try:
        value = json.loads(raw, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return {"manifest": None, "issues": [_issue("", "invalid_json")]}
    return validate_value(value, folder, physical)
