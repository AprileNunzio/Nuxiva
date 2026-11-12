from pathlib import Path

from ._registry import SYSTEM_DIR, AgentRegistry, registry as default_registry

WIDGET_DIR = "widget"
MANIFEST = "widget.json"


def _real_dir(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


def _real_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def agent_bases(registry: AgentRegistry = default_registry) -> list[tuple[str, Path]]:
    return [(a.id, a.dir / WIDGET_DIR) for a in registry.agents() if _real_dir(a.dir / WIDGET_DIR)]


def _children(base: Path) -> list[Path]:
    if not _real_dir(base):
        return []
    return [p / MANIFEST for p in sorted(base.iterdir()) if _real_dir(p) and _real_file(p / MANIFEST)]


def manifests(shared: Path, registry: AgentRegistry = default_registry) -> list[tuple[Path, str]]:
    found = [(p, "") for p in _children(Path(shared))]
    for ident, base in agent_bases(registry):
        found.extend((p, ident) for p in _children(base))
    return found


def system_dirs(shared: Path) -> tuple[Path, ...]:
    return Path(shared), SYSTEM_DIR
