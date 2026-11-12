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
            elif (folder / "feature.json").is_file() and (folder / "tools.py").is_file():
                found[f"{package}.{folder.name}.tools"] = folder.name
                _paths[f"{package}.{folder.name}.tools"] = folder / "tools.py"
    return found


def _signature_of(modules: dict[str, str]) -> str:
    parts = []
    for name in sorted(modules):
        path = _paths.get(name)
        try:
            parts.append(f"{name}:{path.stat().st_mtime_ns}")
        except (OSError, AttributeError):
            parts.append(f"{name}:gone")
    return "|".join(parts)


def _attach(module: str, feature: str) -> int:
    names = [name for name, row in registry.TOOLS.items() if getattr(row["fn"], "__module__", "") == module]
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
    store.event("INFO", f"Strumenti scoperti in «{feature}»: {count}", "tools")


def _unload(module: str, feature: str) -> None:
    gone = [name for name, row in registry.TOOLS.items() if getattr(row["fn"], "__module__", "") == module]
    for name in gone:
        registry.TOOLS.pop(name, None)
    sys.modules.pop(module, None)
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
