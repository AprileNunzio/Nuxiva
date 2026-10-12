import os
import time
import math
import logging
from typing import Dict, Any, List
from server.config.env import settings

logger = logging.getLogger("nuxiva.tools.cad")

def cad_generate_dxf(
    project_id: str,
    part_name: str,
    width_mm: float,
    height_mm: float,
    depth_mm: float = 0.0,
    holes: int = 0,
    hole_diameter_mm: float = 0.0,
) -> Dict[str, Any]:
    """
    Genera un file DXF vettoriale standard (AutoCAD compatibile) contenente contorno, assi e forature.
    """
    output_dir = os.path.join(settings.DATA_DIR, "cad_exports")
    os.makedirs(output_dir, exist_ok=True)
    clean_name = part_name.lower().replace(" ", "_")
    filename = f"{clean_name}_{int(time.time())}.dxf"
    filepath = os.path.join(output_dir, filename)

    # Scrittura di un file ASCII DXF standard valido
    dxf_lines = [
        "0", "SECTION",
        "2", "HEADER",
        "9", "$ACADVER",
        "1", "AC1009", # AutoCAD R12 ASCII DXF (massima compatibilità universale)
        "0", "ENDSEC",
        "0", "SECTION",
        "2", "ENTITIES",
    ]

    # Rettangolo contorno (4 Linee)
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
            "8", "OUTLINE", # Layer
            "10", f"{p1[0]:.3f}",
            "20", f"{p1[1]:.3f}",
            "30", "0.000",
            "11", f"{p2[0]:.3f}",
            "21", f"{p2[1]:.3f}",
            "31", "0.000",
        ])

    # Eventuali forature interne come Cerchi
    if holes > 0 and hole_diameter_mm > 0:
        radius = hole_diameter_mm / 2.0
        # Posiziona fori equispaziati lungo l'asse orizzontale
        spacing = width_mm / (holes + 1)
        center_y = height_mm / 2.0
        for h in range(1, holes + 1):
            center_x = spacing * h
            dxf_lines.extend([
                "0", "CIRCLE",
                "8", "HOLES",
                "10", f"{center_x:.3f}",
                "20", f"{center_y:.3f}",
                "30", "0.000",
                "40", f"{radius:.3f}", # Raggio
            ])

    dxf_lines.extend([
        "0", "ENDSEC",
        "0", "EOF",
    ])

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(dxf_lines))

    # Calcolo coordinate e superfici
    area_sq_mm = width_mm * height_mm
    perimeter_mm = (width_mm + height_mm) * 2.0

    logger.info("CAD DXF generated: %s (Area: %.1f mm²)", filepath, area_sq_mm)

    return {
        "status": "success",
        "part_name": part_name,
        "filename": filename,
        "filepath": filepath,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "depth_mm": depth_mm,
        "holes_count": holes,
        "area_sq_cm": round(area_sq_mm / 100.0, 2),
        "perimeter_cm": round(perimeter_mm / 10.0, 2),
    }

def cad_calculate_bom(
    parts_list: List[Dict[str, Any]],
    material_density_g_cm3: float = 2.7, # Default Alluminio (2.7 g/cm3)
    cost_per_kg_eur: float = 4.5,
) -> Dict[str, Any]:
    """
    Calcola la Distinta Base (BOM), peso totale e stima costi per una serie di particolari tecnici.
    """
    total_weight_kg = 0.0
    items = []

    for p in parts_list:
        width = float(p.get("width_mm", 100))
        height = float(p.get("height_mm", 100))
        depth = float(p.get("depth_mm", 5))
        qty = int(p.get("qty", 1))

        volume_cm3 = (width * height * depth / 1000.0) * qty
        weight_kg = (volume_cm3 * material_density_g_cm3) / 1000.0
        total_weight_kg += weight_kg

        items.append({
            "name": p.get("name", "Particolare"),
            "qty": qty,
            "dimensions_mm": f"{width}x{height}x{depth}",
            "weight_kg": round(weight_kg, 3),
        })

    estimated_cost_eur = round(total_weight_kg * cost_per_kg_eur, 2)

    return {
        "status": "success",
        "items": items,
        "total_parts_count": sum(p.get("qty", 1) for p in parts_list),
        "total_weight_kg": round(total_weight_kg, 2),
        "estimated_material_cost_eur": estimated_cost_eur,
    }
