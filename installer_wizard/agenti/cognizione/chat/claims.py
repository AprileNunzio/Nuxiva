import importlib

from state import store


class ConnectorClaims:
    def __init__(self, connectors: dict[str, str]) -> None:
        self.connectors = connectors
        self.recognizers: dict | None = None

    def _load(self) -> dict:
        found = {}
        for name, module in self.connectors.items():
            try:
                predicate = getattr(importlib.import_module(module), "recognizes", None)
            except Exception as exc:
                store.event("WARN", f"Connettore {name} non caricabile: {exc}", name)
                continue
            if callable(predicate):
                found[name] = predicate
        return found

    def claiming(self, text: str) -> list[str]:
        if self.recognizers is None:
            self.recognizers = self._load()
        hits = []
        for name, predicate in self.recognizers.items():
            try:
                if predicate(text):
                    hits.append(name)
            except Exception as exc:
                store.event("WARN", f"Il connettore {name} non riesce a valutare la richiesta: {exc}", name)
        return hits
