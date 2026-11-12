GAUSSIAN_SKILLS = [
    {
        "id": "anisotropic_sh3_radiance_splatting",
        "domain": "animazioni_3d/volumi",
        "description": "Decomposizione in ellissoidi anisotropici 3D con armoniche sferiche direzionali e controllo di opacità.",
    }
]


def select_gaussian_skill(concept: str) -> dict:
    return dict(GAUSSIAN_SKILLS[0])
