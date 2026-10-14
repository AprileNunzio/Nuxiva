import logging
from typing import Any
from server.core.scanner.base import DiscoveryManifest
from server.features.agent_tools.base import BaseAgentTool

logger = logging.getLogger("nuxiva.tool.generator_3d")

async def generate_3d_model(prompt: str, job_id: str = "react_tool") -> str:
    try:
        from server.core.orchestrator.brain_routing import brain_order_for
        from server.features.parametric.composition import build_designer
        designer = build_designer(lambda: brain_order_for("parametric_designer"))
        result = await designer.design(prompt, job_id)
        files = ", ".join(result.written.values())
        return f"Modello {result.spec.name} generato e validato ({len(result.spec.parts)} parti). File: {files}"
    except Exception as exc:
        logger.warning(f"3D generation failed: {exc}")
        return f"Generazione 3D non riuscita: {exc}"

class Generator3dTool(BaseAgentTool):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id="genera_modello_3d",
            name="Parametric 3D Generator",
            category="tool",
            description="Genera modelli 3D parametrici (OBJ, DXF, AutoLISP) da descrizioni testuali.",
            icon="🧊",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Descrizione testuale dell'oggetto 3D"},
                    "job_id": {"type": "string", "default": "react_tool"},
                },
                "required": ["prompt"],
            },
            metadata={"alias": "generator_3d"},
        )

    async def execute(self, prompt: str, job_id: str = "react_tool", **kwargs: Any) -> str:
        return await generate_3d_model(prompt=prompt, job_id=job_id)
