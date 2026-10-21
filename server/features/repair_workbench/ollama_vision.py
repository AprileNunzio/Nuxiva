import base64
import os
from typing import List

import httpx
from pydantic import ValidationError

from server.features.llm_gateway.gateway import llm_gateway
from server.features.repair_workbench.errors import VisionUnavailableException
from server.features.repair_workbench.session_models import VisionObservation

DEFAULT_MODEL = "qwen2.5vl:7b"
REQUEST_TIMEOUT_SECONDS = 120.0

PROMPT_TEMPLATE = (
    "You are an electronics repair vision analyst. Inspect the photographed board. "
    "Answer in language '{language}' for free-text fields. "
    "Return ONLY a JSON object with keys: title, board_kind, summary, characteristics (list of strings), "
    "components (up to 12 most clearly visible objects with ref, label, value, category, bbox [x1,y1,x2,y2] normalised 0..1, score 0..1, "
    "health one of ok|suspect|fault|unknown, notes), "
    "connections (list of objects with net and pins [{{ref,pin}}]) only for traces you can actually see, "
    "advice (up to 3 short next repair steps). Keep notes under 120 characters and summary under 400 characters. "
    "ref is null when no printed reference is readable; do not invent a board reference. "
    "category must be one of resistor,capacitor,inductor,diode,led,transistor,mosfet,ic,regulator,opamp,"
    "microcontroller,connector,crystal,relay,transformer,fuse,switch,sensor,voltage_source,current_source,other. "
    "Never invent values you cannot read: use an empty string. An unseen trace is not a connection. "
    "A photo alone cannot confirm electrical health: use unknown unless visible damage provides evidence. "
    "Distinguish visible observations from hypotheses and explain what measurement could verify a hypothesis. "
    "Do not identify the board model or purpose without readable evidence. "
    "Every title, label, summary, characteristic, note and advice MUST use language '{language}'; "
    "it means italiano, en English, es español, fr français. Keep schema keys and category enums unchanged. "
    "Already identified references: {known}."
)


class OllamaVisionAnalyzer:
    def __init__(self, model: str = "") -> None:
        self._model = model or os.environ.get("NUXIVA_VISION_MODEL", DEFAULT_MODEL)

    async def analyze(
        self, frame: bytes, language: str, known_refs: List[str]
    ) -> VisionObservation:
        payload = {
            "model": self._model,
            "prompt": PROMPT_TEMPLATE.format(
                language=language, known=", ".join(known_refs[:60]) or "none"
            ),
            "images": [base64.b64encode(frame).decode("ascii")],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        }
        url = f"{llm_gateway.get_ollama_url().rstrip('/')}/api/generate"
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise VisionUnavailableException(type(exc).__name__) from exc
        if not isinstance(body, dict):
            raise VisionUnavailableException("invalid_model_output")
        try:
            observation = VisionObservation.model_validate_json(str(body.get("response", "")))
            observation.model_used = self._model
            return observation
        except ValidationError as exc:
            raise VisionUnavailableException("invalid_model_output") from exc
