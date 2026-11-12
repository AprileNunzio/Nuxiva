from typing import List, Protocol

from server.features.repair_workbench.session_models import VisionObservation


class VisionAnalyzer(Protocol):
    async def analyze(
        self, frame: bytes, language: str, known_refs: List[str]
    ) -> VisionObservation: ...
