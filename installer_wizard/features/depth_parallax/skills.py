DEPTH_PARALLAX_SKILLS = [
    {
        "id": "sobel_bilateral_normal_relief",
        "domain": "animazioni_3d/rilievo_immagini",
        "description": "Estrazione di mappa di profondità da PNG/immagini 2D con calcolo delle normali Sobel e illuminazione speculare 3D.",
    }
]


def select_depth_parallax_skill(concept: str) -> dict:
    return dict(DEPTH_PARALLAX_SKILLS[0])
