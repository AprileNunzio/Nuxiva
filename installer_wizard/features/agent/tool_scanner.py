import importlib
import logging
import re
import sys
import time

from config import FEATURES_DIR
from state import store

from features.agent import registry

log = logging.getLogger("nuxiva.tools")
FEATURE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
CORE = "agent"
PACKAGE = "features"
CHECK_EVERY = 3.0

_loaded: dict[str, str] = {}
_failed: dict[str, str] = {}
_signature = ""
_checked = 0.0


def candidates() -> dict[str, str]:
    found: dict[str, str] = {}
    if not FEATURES_DIR.is_dir():
        return found
    for folder in sorted(FEATURES_DIR.iterdir()):
        if not folder.is_dir() or not FEATURE_ID.fullmatch(folder.name):
            continue
        if folder.name == CORE:
            found.update({f"{PACKAGE}.{CORE}.{path.stem}": CORE for path in sorted(folder.glob("tools_*.py"))})
        elif (folder / "feature.json").is_file() and (folder / "tools.py").is_file():
            found[f"{PACKAGE}.{folder.name}.tools"] = folder.name
    return found


def _signature_of(modules: dict[str, str]) -> str:
    parts = []
    for name in sorted(modules):
        path = FEATURES_DIR.joinpath(*name.split(".")[1:]).with_suffix(".py")
        try:
            parts.append(f"{name}:{path.stat().st_mtime_ns}")
        except OSError:
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
