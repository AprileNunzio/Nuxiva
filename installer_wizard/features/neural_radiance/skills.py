NEURAL_RADIANCE_SKILLS = [
    {
        "id": "sdf_pbr_subsurface_raymarching",
        "domain": "animazioni_3d/fotorealismo",
        "description": "Campi di distanza con segno (SDF) con fusione morbida, Subsurface Scattering, ombre soffuse e occlusione ambientale.",
    }
]


def select_radiance_skill(concept: str) -> dict:
    return dict(NEURAL_RADIANCE_SKILLS[0])
