import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from agenti import _manifest, _scan

log = logging.getLogger("nuxiva.agenti")

APP_DIR = Path(__file__).resolve().parents[1]
SYSTEM_DIR = APP_DIR / "agenti"
LEGACY_DIR = APP_DIR / "features"
CATEGORIES = _manifest.CATEGORIES


def _state_dir() -> Path:
    from config import STATE_DIR
    return Path(STATE_DIR)


def root(path: Path, origin: str, layout: str) -> dict:
    return {"path": str(path), "origin": origin, "layout": layout}


def standard_roots(system: Path | None = None, legacy: Path | None = None, user: Path | None = None) -> list[dict]:
    state = _state_dir()
    return [
        root(system or SYSTEM_DIR, "system", "categorized"),
        root(legacy or LEGACY_DIR, "legacy", "flat"),
        root(state / "agenti", "user", "categorized"),
        root(user or state / "features", "user", "flat"),
    ]


def module_for(folder: Path) -> str:
    folder = Path(folder)
    if not _manifest.valid_id(folder.name):
        return ""
    if folder.parent == LEGACY_DIR:
        return f"features.{folder.name}"
    if folder.parent.parent == SYSTEM_DIR and folder.parent.name in CATEGORIES:
        return f"agenti.{folder.name}"
    return ""


def owner_of(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[0] in ("features", "agenti") else ""


@dataclass(frozen=True)
class Agent:
    id: str
    name: str
    category: str
    dir: Path
    origin: str
    manifest: dict
    issues: tuple

    @property
    def manifest_path(self) -> Path:
        return self.dir / _scan.MANIFEST

    @property
    def module(self) -> str:
        return module_for(self.dir)


def _native_factory():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    factory = getattr(nuxiva_native, "RustAgentRegistry", None)
    return factory() if factory is not None else None


class AgentRegistry:
    def __init__(self, roots: Callable[[], list[dict]] = standard_roots, native: bool = True) -> None:
        self._roots = roots
        self._lock = threading.Lock()
        self._native = _native_factory() if native else None
        self._snap: dict = {"signature": "", "agents": {}, "rejected": [], "by_category": {}, "keywords": {}}
        self._agents: dict[str, Agent] = {}

    @property
    def engine(self) -> str:
        return "rust" if self._native is not None else "python"

    def roots(self) -> list[dict]:
        return [dict(r) for r in self._roots()]

    def refresh(self) -> bool:
        roots = self.roots()
        with self._lock:
            if self._native is not None:
                try:
                    changed = self._native.refresh(json.dumps(roots))
                    if changed or not self._snap["signature"]:
                        self._adopt(json.loads(self._native.snapshot()))
                        return True
                    return False
                except (RuntimeError, ValueError) as exc:
                    log.warning("Registro agenti nativo non disponibile, uso Python: %s", exc)
                    self._native = None
            found = _scan.discover(roots)
            sig = _scan.signature(found)
            if sig == self._snap["signature"] and sig:
                return False
            self._adopt(_scan.build(found, sig))
            return True

    def _adopt(self, snap: dict) -> None:
        self._snap = snap
        self._agents = {
            ident: Agent(ident, e["manifest"]["name"], e["manifest"]["category"], Path(e["dir"]), e["origin"],
                         e["manifest"], tuple(e["issues"]))
            for ident, e in snap["agents"].items()
        }

    def snapshot(self) -> dict:
        self.refresh()
        return self._snap

    def agents(self) -> list[Agent]:
        self.refresh()
        return [self._agents[k] for k in sorted(self._agents)]

    def get(self, ident: str) -> Agent | None:
        self.refresh()
        return self._agents.get(ident)

    def by_category(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self.snapshot()["by_category"].items()}

    def rejected(self) -> list[dict]:
        return list(self.snapshot()["rejected"])

    def manifest_paths(self) -> list[Path]:
        snap = self.snapshot()
        paths = [Path(e["dir"]) / _scan.MANIFEST for e in snap["agents"].values()]
        paths += [Path(r["path"]) for r in snap["rejected"]]
        return sorted(set(paths), key=str)

    def search(self, query: str, limit: int = 10) -> list[tuple[str, int]]:
        self.refresh()
        if self._native is not None:
            return [(i, int(n)) for i, n in self._native.search(query[:4096], limit)]
        return _scan.search(self._snap, query[:4096], limit)

    def bases(self) -> list[Path]:
        out: list[Path] = []
        for r in self.roots():
            base = Path(r["path"])
            if r["layout"] == "flat":
                out.append(base)
            else:
                out.extend(path for _, path in _scan.children(base))
        return out

    def package_dirs(self) -> list[Path]:
        seen: dict[str, Path] = {}
        for base in self.bases():
            for name, path in _scan.children(base):
                seen.setdefault(name, path)
        return [seen[k] for k in sorted(seen)]

    def locate_package(self, ident: str) -> Path | None:
        if not _manifest.valid_id(ident):
            return None
        for base in self.bases():
            candidate = base / ident
            if candidate.is_dir() and not candidate.is_symlink():
                return candidate
        return None


registry = AgentRegistry()
