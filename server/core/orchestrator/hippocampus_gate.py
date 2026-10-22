import logging
import uuid
from typing import Any, Callable, Optional

from server.core.agent_registry.interfaces import AgentTaskResponse
from server.core.hippocampus_router.contracts import Verdict

logger = logging.getLogger("nuxiva.hippocampus.gate")

AGENT_ID = "hippocampus_fast_path"


async def try_fast_path(query: str, language: Optional[str], factory: Callable[[], Any]) -> tuple[Optional[AgentTaskResponse], str]:
    try:
        routed = await factory().route_async(query, language)
    except Exception as exc:
        logger.error("Hippocampus failed (%s): slow path", type(exc).__name__)
        return None, f"slow path · {type(exc).__name__}"
    if not routed.is_ok:
        logger.info("Hippocampus unavailable (%s): slow path", routed.error.code)
        return None, f"slow path · {routed.error.code}"
    outcome = routed.value
    summary = f"{outcome.verdict.value} · {outcome.neuron_id or '-'} · {outcome.latency_ms:.1f} ms"
    if outcome.degraded:
        summary += f" · {outcome.degraded}"
    result = outcome.execution_result
    if outcome.verdict is not Verdict.FAST_PATH or not outcome.executed or not isinstance(result, dict):
        return None, summary
    speech = result.get("speech")
    if not isinstance(speech, str) or not speech.strip():
        return None, summary
    response = AgentTaskResponse(
        task_id=f"tsk_hip_{uuid.uuid4().hex[:10]}",
        agent_id=AGENT_ID,
        status="SUCCESS",
        result_data={"neuron_id": outcome.neuron_id, "verdict": outcome.verdict.value, "result": result},
        speech_output=speech,
        execution_time_ms=outcome.latency_ms,
    )
    return response, summary
