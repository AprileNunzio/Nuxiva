import importlib
import logging
import re
import sys
import time

from agenti._registry import CATEGORIES
from config import AGENTS_DIR
from state import store

from agenti.agent import registry

log = logging.getLogger("nuxiva.tools")
FEATURE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
CORE = "agent"
PACKAGE = "agenti"
CHECK_EVERY = 3.0

_paths: dict[str, object] = {}
_loaded: dict[str, str] = {}
_failed: dict[str, str] = {}
_signature = ""
_checked = 0.0


def _bases() -> list[tuple[object, str]]:
    return [(AGENTS_DIR / name, PACKAGE) for name in CATEGORIES]


def _real_file(path) -> bool:
    return path.is_file() and not path.is_symlink()


def _tools_source(folder):
    if _real_file(folder / "tools.py"):
        return folder / "tools.py"
    package = folder / "tools"
    if package.is_dir() and not package.is_symlink() and _real_file(package / "__init__.py"):
        if any(p.name != "__init__.py" and _real_file(p) for p in package.glob("*.py")):
            return package
    return None


def _stamp(path) -> int:
    if path.is_dir():
        return max((p.stat().st_mtime_ns for p in path.glob("*.py") if not p.is_symlink()), default=0)
    return path.stat().st_mtime_ns


def candidates() -> dict[str, str]:
    found: dict[str, str] = {}
    _paths.clear()
    for base, package in _bases():
        if not base.is_dir():
            continue
        for folder in sorted(base.iterdir()):
            if not folder.is_dir() or folder.is_symlink() or not FEATURE_ID.fullmatch(folder.name):
                continue
            if folder.name == CORE:
                for path in sorted(folder.glob("tools_*.py")):
                    found[f"{package}.{CORE}.{path.stem}"] = CORE
                    _paths[f"{package}.{CORE}.{path.stem}"] = path
            elif (folder / "feature.json").is_file():
                source = _tools_source(folder)
                if source is not None:
                    found[f"{package}.{folder.name}.tools"] = folder.name
                    _paths[f"{package}.{folder.name}.tools"] = source
    return found


def _signature_of(modules: dict[str, str]) -> str:
    parts = []
    for name in sorted(modules):
        path = _paths.get(name)
        try:
            parts.append(f"{name}:{_stamp(path)}")
        except (OSError, AttributeError):
            parts.append(f"{name}:gone")
    return "|".join(parts)


def _owned(name: str, module: str) -> bool:
    return name == module or name.startswith(f"{module}.")


def _attach(module: str, feature: str) -> int:
    names = [name for name, row in registry.TOOLS.items() if _owned(getattr(row["fn"], "__module__", ""), module)]
    for name in names:
        registry.TOOLS[name]["feature"] = feature
    return len(names)


def _load(module: str, feature: str) -> None:
    try:
        importlib.import_module(module)
    except Exception as exc:
        _failed[module] = type(exc).__name__
        log.warning("Strumenti di %s non caricati: %s", feature, exc)
        store.event("WARN", f"Strumenti della funzionalità «{feature}» non caricati: {type(exc).__name__}", "tools")
        return
    _failed.pop(module, None)
    _loaded[module] = feature
    count = _attach(module, feature)
    if count:
        store.event("INFO", f"Strumenti scoperti in «{feature}»: {count}", "tools")


def _unload(module: str, feature: str) -> None:
    gone = [name for name, row in registry.TOOLS.items() if _owned(getattr(row["fn"], "__module__", ""), module)]
    for name in gone:
        registry.TOOLS.pop(name, None)
    for name in [m for m in sys.modules if _owned(m, module)]:
        sys.modules.pop(name, None)
    _loaded.pop(module, None)
    store.event("INFO", f"Strumenti rimossi con «{feature}»: {len(gone)}", "tools")


def sync(force: bool = False) -> bool:
    global _signature, _checked
    now = time.monotonic()
    if not force and _signature and now - _checked < CHECK_EVERY:
        return False
    _checked = now
    wanted = candidates()
    signature = _signature_of(wanted)
    if signature == _signature and not force:
        return False
    _signature = signature
    for module in [m for m in _loaded if m not in wanted]:
        _unload(module, _loaded[module])
    for module, feature in wanted.items():
        if module not in _loaded and module not in _failed:
            _load(module, feature)
    return True


def loaded() -> dict[str, str]:
    return dict(_loaded)


def failed() -> dict[str, str]:
    return dict(_failed)
