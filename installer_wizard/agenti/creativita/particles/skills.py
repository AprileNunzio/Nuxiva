PARTICLE_AGENT_SKILLS = [
    {
        "id": "bioluminescent_marine_zoology",
        "domain": "animali/mare",
        "description": "Sintesi ad altissima densità di cnidari, cefalopodi e organismi abissali con stratificazione esombrellare e tentacolare.",
        "min_parts": 10,
        "target_points": 24_000,
    },
    {
        "id": "neuro_cardiac_anatomy",
        "domain": "anatomia/corpo_umano",
        "description": "Ricostruzione volumetrica di lobi cerebrali, fasci muscolari, strutture vascolari ed eliche genomiche.",
        "min_parts": 9,
        "target_points": 24_000,
    },
    {
        "id": "thermodynamic_propulsion",
        "domain": "auto/motori",
        "description": "Architettura meccanica di bancate cilindri, rotori, statori e camere di combustione.",
        "min_parts": 10,
        "target_points": 20_000,
    },
    {
        "id": "astrophysics_quantum_lattice",
        "domain": "astronomia/cosmo",
        "description": "Sistemi orbitali, anelli planetari, reticoli cristallini e orbitali molecolari.",
        "min_parts": 8,
        "target_points": 20_000,
    },
]


def select_particle_skill(concept: str) -> dict:
    lower = str(concept or "").lower()
    if any(k in lower for k in ("medusa", "rhizostoma", "polp", "calamar", "squalo", "delfin", "balen", "pesce")):
        return dict(PARTICLE_AGENT_SKILLS[0])
    if any(k in lower for k in ("cervell", "cuore", "polmon", "neurone", "dna", "muscol")):
        return dict(PARTICLE_AGENT_SKILLS[1])
    if any(k in lower for k in ("motore", "v8", "turbin", "auto", "aereo", "razzo")):
        return dict(PARTICLE_AGENT_SKILLS[2])
    return dict(PARTICLE_AGENT_SKILLS[3])
