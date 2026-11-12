import json
import os
import secrets
import shutil
from pathlib import Path

from . import _layout
from ._layout import ScaffoldError
from ._registry import SYSTEM_DIR, AgentRegistry, registry as default_registry


def _native(name: str):
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, name, None)


def inspect(directory: Path) -> dict:
    fn = _native("agent_layout_inspect")
    return json.loads(fn(str(directory))) if fn is not None else _layout.inspect(Path(directory))


def files(spec: dict) -> list[tuple[str, bytes]]:
    fn = _native("agent_scaffold")
    if fn is None:
        return _layout.scaffold(spec)
    payload = {"capabilities": [], "nouns": [], "phrases": [], "icon": "", **spec}
    try:
        return [(path, bytes(body)) for path, body in fn(json.dumps(payload, ensure_ascii=False))]
    except ValueError as exc:
        try:
            issues = json.loads(str(exc))
        except ValueError:
            issues = [{"field": "", "code": "invalid_spec", "severity": "error"}]
        raise ScaffoldError(issues) from exc


def similar(spec: dict, registry: AgentRegistry = default_registry, limit: int = 3) -> list[tuple[str, int]]:
    text = " ".join([spec.get("name", ""), spec.get("description", ""), *spec.get("capabilities", []), *spec.get("nouns", [])])
    return [(ident, score) for ident, score in registry.search(text, limit) if score >= 2]


def _safe_base(base: Path) -> Path:
    resolved = base.resolve()
    for part in [base, *base.parents]:
        if part.is_symlink():
            raise ScaffoldError([{"field": "path", "code": "path_symlink", "severity": "error"}])
    return resolved


def create(spec: dict, base: Path = SYSTEM_DIR, registry: AgentRegistry = default_registry) -> Path:
    plan = files(spec)
    ident, category = spec["id"], spec["category"]
    if registry.get(ident) is not None or registry.locate_package(ident) is not None:
        raise ScaffoldError([{"field": "id", "code": "id_duplicate", "severity": "error"}])
    base = _safe_base(Path(base))
    root = base / category
    target = root / ident
    if target.exists() or any(os.path.lexists(base / name / ident) for name in _layout.categories()):
        raise ScaffoldError([{"field": "id", "code": "id_duplicate", "severity": "error"}])
    root.mkdir(parents=True, exist_ok=True, mode=0o755)
    staging = root / f".nuovo-{ident}-{secrets.token_hex(4)}"
    try:
        for rel, body in plan:
            path = (staging / rel).resolve()
            if not path.is_relative_to(staging.resolve()):
                raise ScaffoldError([{"field": "path", "code": "path_escape", "severity": "error"}])
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)
        os.rename(staging, target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    registry.refresh()
    return target
