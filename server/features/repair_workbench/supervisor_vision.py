import base64
import os

import httpx
from pydantic import ValidationError

from server.features.llm_gateway.supervisor_bridge import bridge
from server.features.repair_workbench.errors import VisionUnavailableException
from server.features.repair_workbench.ollama_vision import OllamaVisionAnalyzer
from server.features.repair_workbench.session_models import VisionObservation


class ConfiguredVisionAnalyzer:
    async def analyze(self, frame: bytes, language: str, known_refs: list[str]) -> VisionObservation:
        if os.environ.get("NUXIVA_VISION_MODEL", "").strip():
            return await OllamaVisionAnalyzer().analyze(frame, language, known_refs)
        try:
            response = await bridge._post("/api/internal/repair-workbench/analyze", {
                "frame_base64": base64.b64encode(frame).decode("ascii"),
                "language": language, "known_refs": known_refs,
            }, 145.0)
            response.raise_for_status()
            return VisionObservation.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError) as exc:
            raise VisionUnavailableException("configured_vision_unavailable") from exc
