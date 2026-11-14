import json

import native_core
from personal_graph.fallback import PyGraph


class GraphError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def create_engine(key: bytes | None = None, vault_dir: str | None = None, settings: str | None = None, autosave: bool = True):
    native = native_core.symbol("RustKnowledge")
    if native is not None:
        return native(key, vault_dir, settings, autosave)
    native_core.python_fallback("personal_graph")
    if vault_dir is not None:
        raise GraphError("knowledge.unsupported")
    return PyGraph()


class PersonalGraph:
    def __init__(self, engine=None):
        self.engine = engine if engine is not None else create_engine()

    def call(self, op: str, **fields):
        reply = json.loads(self.engine.handle(json.dumps({"op": op, **fields}, ensure_ascii=False)))
        if not reply.get("ok"):
            raise GraphError(reply.get("error", "knowledge.invalid"))
        return reply.get("data")

    def register(self, person: str, name: str, role: str, consent: bool = True):
        return self.call("register", id=person, name=name, role=role, consent=consent)

    def learn(self, person: str, text: str, reference: str = ""):
        return self.call("extract", **{"as": person, "text": text, "reference": reference})

    def search(self, person: str, text: str, **query):
        return self.call("search", **{"as": person, "query": {"text": text, **query}})

    def neighbors(self, person: str, **query):
        return self.call("neighbors", **{"as": person, "query": query})

    def correct(self, person: str, correction: dict):
        return self.call("correct", **{"as": person, "correction": correction})

    def export(self, person: str):
        return self.call("export", **{"as": person})

    def erase(self, person: str):
        return self.call("erase", **{"as": person, "confirm": "ERASE:" + person})
