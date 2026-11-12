import importlib
import importlib.abc
import importlib.machinery
import sys
from pathlib import Path

from agenti import _manifest

PACKAGE = "agenti"
ROOT = Path(__file__).resolve().parent
LEGACY_DIR = ROOT.parent / "features"


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
    def __init__(self, root: Path = ROOT, legacy: Path = LEGACY_DIR) -> None:
        self.root = root
        self.legacy = legacy

    def find_spec(self, fullname: str, path=None, target=None):
        if not fullname.startswith(PACKAGE + "."):
            return None
        parts = fullname.split(".")
        head = parts[1]
        if head in _manifest.CATEGORIES:
            raise ModuleNotFoundError(f"Gli agenti si importano per id (agenti.<id>), non per categoria: {fullname}",
                                      name=fullname)
        if not _manifest.valid_id(head):
            return None
        if any(_real_dir(self.root / category / head) for category in _manifest.CATEGORIES):
            return None
        if not _real_dir(self.legacy / head):
            return None
        alias = "features." + ".".join(parts[1:])
        return importlib.machinery.ModuleSpec(fullname, _Alias(alias))


def install() -> AgentFinder:
    for finder in sys.meta_path:
        if isinstance(finder, AgentFinder):
            return finder
    finder = AgentFinder()
    sys.meta_path.insert(0, finder)
    return finder
