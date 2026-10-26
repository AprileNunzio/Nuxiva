import os
import time
import logging
from typing import Dict, Any
from server.config.env import settings
from server.core.scanner.base import DiscoveryManifest
from server.features.agent_tools.base import BaseAgentTool

logger = logging.getLogger("nuxiva.tool.cad")

def cad_generate_dxf(
    project_id: str,
    part_name: str,
    width_mm: float,
    height_mm: float,
    depth_mm: float = 0.0,
    holes: int = 0,
    hole_diameter_mm: float = 0.0,
) -> Dict[str, Any]:
    output_dir = os.path.join(settings.DATA_DIR, "cad_exports")
    os.makedirs(output_dir, exist_ok=True)
    clean_name = part_name.lower().replace(" ", "_")
    filename = f"{clean_name}_{int(time.time())}.dxf"
    filepath = os.path.join(output_dir, filename)

    dxf_lines = [
        "0", "SECTION",
        "2", "HEADER",
        "9", "$ACADVER",
        "1", "AC1009",
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
    ]

    points = [
        (0.0, 0.0),
        (width_mm, 0.0),
        (width_mm, height_mm),
        (0.0, height_mm),
    ]

    for i in range(4):
        p1 = points[i]
        p2 = points[(i + 1) % 4]
        dxf_lines.extend([
            "0", "LINE",
            "8", "OUTLINE",
            "10", f"{p1[0]:.3f}",
            "20", f"{p1[1]:.3f}",
            "30", "0.000",
            "11", f"{p2[0]:.3f}",
            "21", f"{p2[1]:.3f}",
            "31", "0.000",
        ])

    if holes > 0 and hole_diameter_mm > 0:
        radius = hole_diameter_mm / 2.0
        step_x = width_mm / (holes + 1)
        cy = height_mm / 2.0
        for h in range(holes):
            cx = step_x * (h + 1)
            dxf_lines.extend([
                "0", "CIRCLE",
                "8", "HOLES",
                "10", f"{cx:.3f}",
                "20", f"{cy:.3f}",
                "30", "0.000",
                "40", f"{radius:.3f}",
            ])

    dxf_lines.extend([
        "0", "ENDSEC",
        "0", "EOF",
    ])

    with open(filepath, "w", encoding="ascii") as f:
        f.write("\n".join(dxf_lines) + "\n")

    return {
        "status": "SUCCESS",
        "file_name": filename,
        "file_path": filepath,
        "part_name": part_name,
        "dimensions": {
            "width": width_mm,
            "height": height_mm,
            "depth": depth_mm,
            "holes": holes,
            "hole_diameter": hole_diameter_mm,
        },
        "preview_type": "dxf_vector",
    }

class CadTool(BaseAgentTool):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id="cad_generate_dxf",
            name="CAD DXF Generator",
            category="tool",
            description="Genera file DXF vettoriali standard per lavorazioni meccaniche.",
            icon="📐",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "part_name": {"type": "string"},
                    "width_mm": {"type": "number"},
                    "height_mm": {"type": "number"},
                    "depth_mm": {"type": "number", "default": 0.0},
                    "holes": {"type": "integer", "default": 0},
                    "hole_diameter_mm": {"type": "number", "default": 0.0},
                },
                "required": ["project_id", "part_name", "width_mm", "height_mm"],
            },
            metadata={"alias": "cad"},
        )

    async def execute(
        self,
        project_id: str,
        part_name: str,
        width_mm: float,
        height_mm: float,
        depth_mm: float = 0.0,
        holes: int = 0,
        hole_diameter_mm: float = 0.0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return cad_generate_dxf(
            project_id=project_id,
            part_name=part_name,
            width_mm=width_mm,
            height_mm=height_mm,
            depth_mm=depth_mm,
            holes=holes,
            hole_diameter_mm=hole_diameter_mm,
        )
