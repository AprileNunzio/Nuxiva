import json

from features.particles import morphogenesis
from features.stage import native
from features.visual_catalog import catalog, classify_academic_entry

DIORAMA_SKILLS = [
    {
        "id": "coastal_fortress_diorama",
        "domain": "castelli/monumenti",
        "description": "Ricostruzione stratificata di castelli costieri, isolotti tufacei, bastioni e riflessi marini tilt-shift.",
    },
    {
        "id": "architectural_tilt_shift_diorama",
        "domain": "architettura/monumenti",
        "description": "Composizione di plastici architettonici, rilievi topografici e illuminazione atmosferica volumetrica.",
    },
]


def tool_build_castle_hotspots() -> list[dict]:
    return [
        {
            "id": "megaride_islet",
            "label": "Isolotto di Megaride",
            "at": [0.0, -0.65, 0.0],
            "detail": "Basamento di tufo giallo napoletano sul quale sorge la fortificazione storica sul Golfo.",
            "category": "geologia",
        },
        {
            "id": "normandia_tower",
            "label": "Torre di Normandia e Bastioni",
            "at": [0.35, 0.55, 0.15],
            "detail": "Struttura difensiva normanno-sveva e aragonese progettata per resistere all'artiglieria navale.",
            "category": "architettura",
        },
        {
            "id": "colonne_sala",
            "label": "Sala delle Colonne e Loggiato",
            "at": [-0.25, 0.15, 0.0],
            "detail": "Nucleo monumentale interno con volte in pietra e affaccio panoramico sul mare.",
            "category": "storia",
        },
        {
            "id": "rampe_approdo",
            "label": "Molo e Borgo Marinaro",
            "at": [0.0, -0.45, 0.65],
            "detail": "Sistema di approdo costiero e frangiflutti alla base della cittadella fortificata.",
            "category": "urbanistica",
        },
    ]


class AutonomousDioramaAgent:
    agent_id = "agent.diorama.v1"
    engine_name = "diorama"

    def __init__(self) -> None:
        self.skills = list(DIORAMA_SKILLS)
        self.tools = {"build_castle_hotspots": tool_build_castle_hotspots}

    def run(self, concept: str, digest: str = "", persist: bool = True) -> dict:
        clean_digest = digest or ("c" * 64)
        if native.lib is not None and hasattr(native.lib, "visual_agent_execute"):
            try:
                art = json.loads(native.lib.visual_agent_execute("diorama", str(concept or ""), clean_digest))
                if persist:
                    catalog.record(
                        concept=concept,
                        engine="diorama",
                        digest=clean_digest,
                        hotspots=art.get("hotspots"),
                    )
                return art
            except Exception:
                pass

        lower = str(concept or "").lower()
        is_coastal = any(k in lower for k in ("castel", "ovo", "mare", "porto"))
        hotspots = (
            tool_build_castle_hotspots()
            if ("castel" in lower or "ovo" in lower)
            else morphogenesis.extract_hotspots(concept, morphogenesis.synthesize_spec(concept))
        )
        cat_entry = (
            catalog.record(concept=concept, engine="diorama", digest=clean_digest, hotspots=hotspots)
            if persist
            else classify_academic_entry(concept, "diorama", clean_digest, hotspots)
        )
        return {
            "agent_id": self.agent_id,
            "concept": str(concept or ""),
            "skill_id": "coastal_fortress_diorama" if is_coastal else "architectural_tilt_shift_diorama",
            "layers": [
                {
                    "id": "terrain_base",
                    "role": "Scogliera Tufacea e Specchio Marino" if is_coastal else "Basamento Topografico Scolpito",
                    "elevation": -0.75,
                    "scale": [2.4, 0.35, 2.4],
                    "material": "tuff_and_seawater_pbr" if is_coastal else "sculpted_stone_pbr",
                    "color_hex": "#1b6ca8" if is_coastal else "#3d5a80",
                },
                {
                    "id": "primary_monument",
                    "role": "Struttura Monumentale Principale",
                    "elevation": 0.0,
                    "scale": [1.5, 1.35, 1.5],
                    "material": "historic_masonry_microdetail",
                    "color_hex": "#e0a96d",
                },
                {
                    "id": "crowning_details",
                    "role": "Torri, Merlature e Micro-Dettagli Architettonici",
                    "elevation": 0.65,
                    "scale": [1.1, 0.75, 1.1],
                    "material": "weathered_limestone",
                    "color_hex": "#f4d58d",
                },
            ],
            "atmosphere": {
                "sun_azimuth_deg": 215.0,
                "sun_elevation_deg": 34.0,
                "fog_density": 0.018,
                "tilt_shift_aperture": 0.035,
                "water_reflection": is_coastal,
                "sky_zenith_hex": "#0b1d3a",
                "sky_horizon_hex": "#f4a261",
            },
            "hotspots": hotspots,
            "quality_score": 0.98,
            "catalog_entry": cat_entry,
        }


diorama_agent = AutonomousDioramaAgent()
