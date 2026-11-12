import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

LANGUAGE = Path(__file__).resolve().parents[1] / "language"
MAX_SPOTS = 8
ORDER = ("head", "snout", "beak", "ears", "horns", "neck", "body", "thorax", "abdomen", "front_legs", "hind_legs", "legs", "arms", "wings",
         "fins", "tail")


@dataclass(frozen=True)
class Hotspot3D:
    id: str
    label: str
    at: tuple[float, float, float]
    detail: str
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=8)
def _names(lang: str) -> dict:
    try:
        return json.loads((LANGUAGE / f"{lang}.json").read_text(encoding="utf-8")).get("parts", {})
    except (OSError, ValueError):
        return {}


def _labelled(spec: dict, lang: str) -> list[dict]:
    parts = spec.get("parts") or []
    reach = max((max(abs(v) for v in p["at"]) + max(p["size"]) for p in parts), default=0.0) or 1.0
    names = _names(lang) or _names("it")
    spots = []
    for item in sorted(spec.get("labels") or [], key=lambda item: ORDER.index(item["name"]) if item["name"] in ORDER else len(ORDER)):
        info = names.get(item["name"])
        if info:
            at = tuple(v / reach for v in item["at"])
            spots.append(Hotspot3D(item["name"], info["label"], at, info["detail"], "anatomia").to_dict())
    return spots[:MAX_SPOTS]


def extract_hotspots(concept: str, spec: dict, lang: str = "it") -> list[dict]:
    lower = str(concept or "").lower()
    spots = _labelled(spec or {}, lang)
    if spots:
        return spots

    if any(k in lower for k in ("cervell", "brain")):
        return [
            Hotspot3D("frontal_lobe", "Lobo Frontale", (0.0, 0.45, 0.35),
                      "Pianificazione strategica, decisione e pensiero logico astratto.", "anatomia").to_dict(),
            Hotspot3D("temporal_lobes", "Lobi Temporali", (-0.45, 0.1, 0.0),
                      "Elaborazione del linguaggio, memoria semantica e riconoscimento uditivo.", "anatomia").to_dict(),
            Hotspot3D("cerebellum", "Cervelletto", (0.0, -0.45, -0.45),
                      "Coordinamento motorio fine, equilibrio e postura corporea.", "funzione").to_dict(),
            Hotspot3D("brainstem", "Tronco Encefalico", (0.0, -0.75, -0.1),
                      "Regolazione dei ritmi vitali involontari, respiro e battito cardiaco.", "fisiologia").to_dict(),
        ]

    if any(k in lower for k in ("medusa", "jellyfish", "cnidar")):
        return [
            Hotspot3D("umbrella", "Esombrella", (0.0, 0.85, 0.0),
                      "Cupola gelatinosa a contrazione idrodinamica pulsante per il nuoto.", "struttura").to_dict(),
            Hotspot3D("subumbrella", "Anello Subombrellare", (0.0, 0.45, 0.0),
                      "Fasci muscolari circolari che generano la spinta idraulica ritmica.", "motoria").to_dict(),
            Hotspot3D("gastrovascular", "Cavità Gastrovascolare", (0.0, 0.15, 0.0),
                      "Sistema digerente e distributivo dei nutrienti cellulari.", "nutrizione").to_dict(),
            Hotspot3D("tentacles", "Tentacoli e Cnidociti", (0.6, -0.75, 0.0),
                      "Filamenti urticanti per la difesa e la cattura di prede tramite microscopici arpioni.", "difesa").to_dict(),
        ]

    if any(k in lower for k in ("motore", "engine", "turbin")):
        return [
            Hotspot3D("combustion", "Camera di Combustione", (0.0, 0.2, 0.0),
                      "Zona di espansione termodinamica del fluido ad alta pressione.", "energia").to_dict(),
            Hotspot3D("stator", "Stadio Rotorico", (-0.55, 0.0, 0.0),
                      "Palette calettate per la conversione dell'energia cinetica in coppia motrice.", "meccanica").to_dict(),
            Hotspot3D("exhaust", "Ugello di Scarico", (0.85, 0.0, 0.0),
                      "Accelerazione supersonica dei gas combusti per la spinta propulsiva.", "fluidodinamica").to_dict(),
        ]

    parts = (spec or {}).get("parts") or []
    for idx, part in enumerate(parts[:4]):
        at = part.get("at") or [0.0, 0.0, 0.0]
        pos = (float(at[0]), float(at[1]), float(at[2])) if len(at) >= 3 else (0.0, 0.0, 0.0)
        spots.append(Hotspot3D(
            f"part_{idx}",
            f"Elemento {idx + 1}",
            pos,
            "Componente strutturale tridimensionale della morfologia olografica.",
            "struttura",
        ).to_dict())
    return spots
