import importlib
import importlib.abc
import importlib.machinery
import sys
from pathlib import Path

from . import _manifest

PACKAGE = "agenti"
LEGACY_PACKAGE = "features"
ROOT = Path(__file__).resolve().parent


class _Alias(importlib.abc.Loader):
    def __init__(self, target: str) -> None:
        self.target = target

    def create_module(self, spec):
        return importlib.import_module(self.target)

    def exec_module(self, module) -> None:
        return None


def _real_dir(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


class AgentFinder(importlib.abc.MetaPathFinder):
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root

    def _installed(self, ident: str) -> bool:
        return _manifest.valid_id(ident) and any(
            _real_dir(self.root / category / ident) for category in _manifest.CATEGORIES)

    def find_spec(self, fullname: str, path=None, target=None):
        parts = fullname.split(".")
        if len(parts) < 2:
            return None
        if parts[0] == PACKAGE and parts[1] in _manifest.CATEGORIES:
            raise ModuleNotFoundError(f"Gli agenti si importano per id (agenti.<id>), non per categoria: {fullname}",
                                      name=fullname)
        if parts[0] == LEGACY_PACKAGE and self._installed(parts[1]):
            return importlib.machinery.ModuleSpec(fullname, _Alias(".".join([PACKAGE, *parts[1:]])))
        return None


def install() -> AgentFinder:
    for finder in sys.meta_path:
        if isinstance(finder, AgentFinder):
            return finder
    finder = AgentFinder()
    sys.meta_path.insert(0, finder)
    return finder
