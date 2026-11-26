import json
import time

from agenti.reasoning import contracts, state

REFRESH_SECONDS = 60
_last = {"at": 0.0, "fingerprint": "", "inferred": 0, "count": 0}


def _tools() -> tuple[list[dict], object]:
    from agenti.agent import registry
    from agenti.capabilities.schema import input_schema
    return registry.available("completo"), input_schema


def _connectors() -> dict[str, str]:
    from agenti._registry import registry as agents
    from agenti.chat import assistant
    out = {}
    for name, module in assistant.CONNECTORS.items():
        parts = module.split(".")
        found = agents.get(parts[1]) if len(parts) > 1 else None
        out[name] = (found.manifest.get("description") if found else "") or name
    return out


def _chat_summary() -> str:
    from agenti._registry import registry as agents
    found = agents.get("chat")
    return (found.manifest.get("description") if found else "") or "Conversation answer"


def build() -> dict:
    tools, schema_of = _tools()
    return contracts.document(tools, schema_of, _connectors(), _chat_summary())


def sync(force: bool = False) -> dict:
    if not force and _last["fingerprint"] and time.monotonic() - _last["at"] < REFRESH_SECONDS:
        return dict(_last)
    doc = build()
    fingerprint = contracts.fingerprint(doc)
    if force or fingerprint != _last["fingerprint"]:
        _last["count"] = state.engine().load_registry(json.dumps(doc))
        _last["fingerprint"] = fingerprint
        _last["inferred"] = contracts.inferred(doc)
    _last["at"] = time.monotonic()
    return dict(_last)
