from typing import List, Dict, Any, Optional
from server.core.telemetry.journey import journey

class CognitiveFlowService:
    @staticmethod
    def get_active_flow() -> Optional[Dict[str, Any]]:
        active = journey.active()
        if active:
            return active.snapshot()
        recent = journey.recent()
        if recent:
            return recent[0]
        return None

    @staticmethod
    def get_recent_flows(limit: int = 10) -> List[Dict[str, Any]]:
        items = journey.recent()
        return items[:limit]



cognitive_flow_service = CognitiveFlowService()
