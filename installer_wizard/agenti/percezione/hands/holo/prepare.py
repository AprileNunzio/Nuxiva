import json

import native_module

from agenti.hands.holo import fallback


def prepare(spec: dict) -> dict:
    engine = native_module.feature("holo_prepare")
    if engine is None:
        native_module.python_fallback("holo")
        return fallback.prepare(spec)
    return json.loads(engine(json.dumps(spec, ensure_ascii=False, separators=(",", ":"))))
