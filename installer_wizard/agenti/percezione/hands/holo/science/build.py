import json

import native_module

from agenti.hands.holo import fallback as holo_fallback
from agenti.hands.holo.science import fallback

GENERATED_PARTS = 400


def scene(kind: str, text: str, title: str) -> dict:
    engine = native_module.feature("holo_molecule")
    if engine is not None:
        return json.loads(engine(kind, text, title))
    native_module.python_fallback("holo")
    parts = fallback.sdf_parts(text) if kind == "sdf" else fallback.pdb_parts(text)
    return holo_fallback.prepare({"title": title, "source": "model", "parts": parts}, GENERATED_PARTS)
