import hashlib
import json
import time

from agenti.agent import registry
from agenti.mcpclient import engine

CONSENT = "mcp.consent.required"
ASKED: dict[tuple[str, str], float] = {}


def operation() -> str:
    return hashlib.sha256(registry.REQUEST.get().encode()).hexdigest()[:32]


def confirm(tool_id: str) -> bool:
    now = time.monotonic()
    for key in [k for k, t in ASKED.items() if now - t > engine.consent_ttl()]:
        ASKED.pop(key, None)
    needed = engine.get().needs_consent(tool_id, operation())
    if needed:
        ASKED[(tool_id, operation())] = now
    return needed


def attempt(core, request: dict, budgeted: bool) -> dict:
    if not budgeted:
        return {"state": "done", "output": json.loads(core.call(json.dumps(request)))}
    return json.loads(core.call_budgeted(json.dumps(request)))


def invoke(tool_id: str, arguments: dict, op: str, agent: str = engine.AGENT, budgeted: bool = False) -> dict:
    core = engine.get()
    request = {"tool": tool_id, "principal": engine.PRINCIPAL, "agent": agent, "operation": op, "arguments": arguments}
    try:
        result = attempt(core, request, budgeted)
    except engine.rejected() as exc:
        code = str(exc.args[0]) if exc.args else ""
        if code != CONSENT or ASKED.pop((tool_id, op), None) is None:
            raise PermissionError(code or "mcp.rejected") from exc
        request["consent"] = core.request_consent(json.dumps(request))
        result = attempt(core, request, budgeted)
    return result if budgeted else result["output"]
