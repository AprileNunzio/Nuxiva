import hashlib
import json
import re

ID = re.compile(r"[a-z0-9_.]{1,64}")
PARAM = re.compile(r"[a-z0-9_.]{1,64}")
TYPES = {"string": "text", "integer": "number", "number": "number", "boolean": "bool", "object": "json", "array": "json"}
EFFECTS = ("read", "write", "send_external", "spend", "physical")
IRREVERSIBLE = {"send_external", "spend"}
MAX_SUMMARY = 236
CHAT = "chat.answer"
CONNECTOR = "connector."
NODE = "server"


def summary(text: str) -> str:
    flat = " ".join(str(text or "").split())
    flat = "".join(ch for ch in flat if ch.isprintable())
    if len(flat.encode("utf-8")) <= MAX_SUMMARY:
        return flat or "-"
    cut = flat.encode("utf-8")[:MAX_SUMMARY].decode("utf-8", "ignore")
    return cut.rsplit(" ", 1)[0] or cut


def effects_of(row: dict) -> tuple[list[str], bool, bool]:
    declared = [e for e in row.get("effects") or () if e in EFFECTS]
    if declared:
        return sorted(set(declared)), not (set(declared) & IRREVERSIBLE), False
    if row.get("confirm"):
        return ["send_external", "write"], False, True
    return ["read"], True, True


def inputs_of(name: str, schema_of) -> list[dict]:
    schema = schema_of(name)
    required = set(schema.get("required", []))
    params = []
    for key, spec in list(schema.get("properties", {}).items())[:24]:
        if not PARAM.fullmatch(key):
            continue
        params.append({"name": key, "ty": TYPES.get(spec.get("type"), "text"), "required": key in required})
    return params


def tool_contract(row: dict, schema_of) -> dict | None:
    name = row.get("name", "")
    if not ID.fullmatch(name) or name.startswith((CONNECTOR, CHAT)):
        return None
    effects, reversible, inferred = effects_of(row)
    tags = ["tool"] + (["inferred"] if inferred else []) + ([row["agent"]] if ID.fullmatch(row.get("agent") or "") else [])
    return {"id": name, "version": 1, "origin": "local", "summary": summary(row.get("description")),
            "inputs": inputs_of(name, schema_of), "output": "text", "effects": effects, "reversible": reversible,
            "min_role": "family" if row.get("full_only") or not reversible else "guest", "nodes": [NODE], "tags": tags[:12]}


def connector_contract(name: str, description: str) -> dict | None:
    ident = f"{CONNECTOR}{name}"
    if not ID.fullmatch(ident):
        return None
    return {"id": ident, "version": 1, "origin": "local", "summary": summary(description or name),
            "inputs": [{"name": "request", "ty": "text", "required": True}], "output": "text", "effects": ["read"],
            "reversible": True, "min_role": "guest", "nodes": [NODE], "tags": ["connector", "inferred"]}


def chat_contract(description: str) -> dict:
    return {"id": CHAT, "version": 1, "origin": "local", "summary": summary(description),
            "inputs": [{"name": "question", "ty": "text", "required": True}], "output": "text", "effects": ["read"],
            "reversible": True, "min_role": "guest", "nodes": [NODE], "tags": ["chat"]}


def document(tools: list[dict], schema_of, connectors: dict[str, str], chat_summary: str) -> dict:
    capabilities, seen = [], set()
    candidates = [tool_contract(t, schema_of) for t in tools]
    candidates += [connector_contract(name, text) for name, text in sorted(connectors.items())]
    candidates.append(chat_contract(chat_summary))
    for contract in candidates:
        if contract and contract["id"] not in seen:
            seen.add(contract["id"])
            capabilities.append(contract)
    return {"schema": 1, "capabilities": capabilities}


def fingerprint(doc: dict) -> str:
    return hashlib.blake2b(json.dumps(doc, sort_keys=True).encode(), digest_size=16).hexdigest()


def inferred(doc: dict) -> int:
    return sum(1 for c in doc["capabilities"] if "inferred" in c.get("tags", []))
