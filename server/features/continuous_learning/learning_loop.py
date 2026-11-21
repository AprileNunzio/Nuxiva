import logging
from typing import Any, Dict, Optional

from server.core.agent_registry.interfaces import AgentTaskResponse
from server.core.orchestrator.skill_acquisition import acquire_missing_skill

logger = logging.getLogger("nuxiva.continuous_learning")


class ContinuousLearningEngine:
    def __init__(self) -> None:
        self.is_learning: bool = False
        self.max_repair_attempts: int = 3

    def classify_failure(self, failure_reason: str) -> str:
        lower = failure_reason.lower()
        if "404" in lower or "endpoint" in lower:
            return "endpoint_relocated"
        if "schema" in lower or "keyerror" in lower or "json" in lower:
            return "schema_drift"
        if "401" in lower or "403" in lower or "auth" in lower:
            return "auth_expired"
        if "forbidden" in lower or "guard" in lower:
            return "sandbox_guard_violation"
        return "missing_capability"

    async def handle_failure(
        self,
        task_query: str,
        failure_reason: str,
        orchestrator_ref: Any = None,
        task_id: str = "self_heal",
        intent: str = "dynamic_recovery",
        device_id: str = "local_node",
    ) -> AgentTaskResponse:
        self.is_learning = True
        cause = self.classify_failure(failure_reason)
        enriched_goal = f"{task_query} [recovery_cause={cause}]"
        response = await acquire_missing_skill(
            task_id=task_id,
            intent=intent,
            query=enriched_goal,
            device_id=device_id,
        )
        self.is_learning = False
        return response


learning_engine = ContinuousLearningEngine()
