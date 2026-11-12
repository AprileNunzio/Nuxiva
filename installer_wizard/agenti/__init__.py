import importlib
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
__path__ = [str(_ROOT)]

from . import _loader, _manifest

_CATEGORIES = _manifest.CATEGORIES
__path__.extend(str(_ROOT / name) for name in _CATEGORIES)
_loader.install()


class _CategoryView:
    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:
        return f"<categoria di agenti {self._name}>"

    def __dir__(self) -> list[str]:
        from ._registry import registry
        return sorted(registry.by_category().get(self._name, []))

    def __getattr__(self, ident: str):
        from ._registry import registry
        agent = registry.get(ident) if _manifest.valid_id(ident) else None
        if agent is None or agent.category != self._name:
            raise AttributeError(f"Nessun agente «{ident}» nella categoria «{self._name}»")
        return importlib.import_module(f".{ident}", __name__)


def __getattr__(name: str):
    if name == "registry":
        from ._registry import registry
        return registry
    if name in _CATEGORIES:
        return _CategoryView(name)
    if _manifest.valid_id(name):
        try:
            return importlib.import_module(f".{name}", __name__)
        except ModuleNotFoundError as exc:
            raise AttributeError(f"Agente non trovato: {name}") from exc
    raise AttributeError(name)
