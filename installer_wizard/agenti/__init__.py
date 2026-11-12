import importlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FEATURES_DIR = BASE_DIR / "features"


class _AgentNamespace:
    def __init__(self, category: str = "") -> None:
        self._category = category

    def __getattr__(self, name: str):
        flat_mod = f"features.{name}"
        try:
            return importlib.import_module(flat_mod)
        except ImportError:
            pass
        if self._category:
            cat_mod = f"features.{self._category}.{name}"
            try:
                return importlib.import_module(cat_mod)
            except ImportError:
                pass
        raise AttributeError(f"Agente non trovato: {name}")


creativita = _AgentNamespace("creativita")
sicurezza = _AgentNamespace("sicurezza")
percezione = _AgentNamespace("percezione")
cognizione = _AgentNamespace("cognizione")
domotica = _AgentNamespace("domotica")
infrastruttura = _AgentNamespace("infrastruttura")
multimedia = _AgentNamespace("multimedia")


def __getattr__(name: str):
    categories = {
        "creativita": creativita,
        "sicurezza": sicurezza,
        "percezione": percezione,
        "cognizione": cognizione,
        "domotica": domotica,
        "infrastruttura": infrastruttura,
        "multimedia": multimedia,
    }
    if name in categories:
        return categories[name]
    return getattr(_AgentNamespace(), name)
