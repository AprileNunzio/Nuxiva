from agenti.sentinel import record
from agenti.system_logs.service import redact

MCP_METHODS = frozenset({"initialize", "ping", "tools/list", "tools/call", "resources/list", "resources/read",
                         "resources/templates/list", "prompts/list", "prompts/get"})

def _safe(value: object) -> str:
    return " ".join(redact(str(value or "")).split())[:120]


def chat(channel: str, journey_id: str, result: dict) -> None:
    ceo = result.get("ceo") or {}
    status = result.get("execution_status") or ("failed" if result.get("error") else "unverified")
    record.record("self.chat_request", record.NUXIVA, "sentinel.self.chat_request", {
        "channel": _safe(channel), "journey": _safe(journey_id), "intent": _safe(result.get("intent")),
        "planned": _safe(ceo.get("planned_agent")), "executor": _safe(ceo.get("reported_executor") or result.get("agent")),
        "status": _safe(status), "verified": "yes" if result.get("verified") is True else "no",
    }, source="chat")


def mcp(method: str, tool: object, status: str, elapsed_ms: int) -> None:
    record.record("self.mcp_request", record.NUXIVA, "sentinel.self.mcp_request", {
        "method": method if method in MCP_METHODS else "unknown", "tool": _safe(tool), "status": status, "ms": elapsed_ms,
    }, source="mcp")
