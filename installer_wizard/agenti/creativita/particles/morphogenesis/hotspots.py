from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Hotspot3D:
    id: str
    label: str
    at: tuple[float, float, float]
    detail: str
    category: str

    def to_dict(self) -> dict:
        return asdict(self)


def extract_hotspots(concept: str, spec: dict) -> list[dict]:
    lower = str(concept or "").lower()
    spots = []

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
