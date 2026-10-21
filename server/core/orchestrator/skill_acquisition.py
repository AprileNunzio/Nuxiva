import time
from server.core.agent_registry.interfaces import AgentTaskResponse
from server.core.context_graph.graph_client import graph_client
from server.core.context_graph.node_schema import NodeType
from server.features.skill_synthesis.synthesizer_lobe import skill_synthesizer

async def acquire_missing_skill(task_id: str, intent: str, query: str, device_id: str) -> AgentTaskResponse:
    started = time.time()
    outcome = await skill_synthesizer.acquire({
        "missing_intent": intent,
        "context": {"query": query, "device_id": device_id},
    })
    graph_client.upsert_node(
        node_id=task_id,
        node_type=NodeType.CONCEPT,
        label=f"Task: {query[:40]}",
        properties={"status": "COMPLETED" if outcome.ok else "FAILED", "acquired_tool": outcome.tool_name},
    )
    if not outcome.ok:
        return AgentTaskResponse(
            task_id=task_id,
            agent_id="skill_synthesizer",
            status="SYNTHESIS_FAILED",
            result_data={"reason": outcome.message, "attempts": outcome.attempts},
            speech_output=outcome.speech,
            execution_time_ms=(time.time() - started) * 1000,
        )
    return AgentTaskResponse(
        task_id=task_id,
        agent_id="skill_synthesizer",
        status="SUCCESS",
        result_data={
            "tool": outcome.tool_name,
            "data": outcome.data,
            "egress_hosts": list(outcome.egress_hosts),
            "attempts": outcome.attempts,
            "acquired": True,
        },
        speech_output=outcome.speech,
        execution_time_ms=(time.time() - started) * 1000,
    )
