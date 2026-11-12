import native_core

from agenti.ear.distress import py_analyze

SPEECH_ALARM = 0.5
ALL_CLEAR = 0.95


def detect_speech_intent(text: str, prefer_native: bool = True) -> tuple[str | None, float]:
    if not text or not isinstance(text, str):
        return None, 0.0
    fn = native_core.symbol("rescue_detect_speech") if prefer_native else None
    if fn is not None:
        return fn(text)
    verdict = py_analyze(text, False, False, 1.0)
    best = ("", 0.0)
    for item in (("help_words", verdict["help"]), ("fire", verdict["fire"]), ("violence", verdict["threat"])):
        if item[1] > best[1]:
            best = item
    if best[1] >= SPEECH_ALARM:
        return best
    if verdict["answer"] == "ok":
        return "all_clear", ALL_CLEAR
    return None, 0.0


def detect_visual_distress(detections: list[dict], prefer_native: bool = True) -> tuple[str | None, float, dict]:
    if not detections:
        return None, 0.0, {}
    fn = native_core.symbol("rescue_detect_visual") if prefer_native else None
    for d in detections:
        cls = str(d.get("class") or "").lower()
        score = float(d.get("score", 0.0))
        bbox = d.get("bbox") or d.get("box") or [0.0, 0.0, 0.0, 0.0]
        w = float(bbox[2]) if len(bbox) >= 3 else 0.0
        h = float(bbox[3]) if len(bbox) >= 4 else 0.0
        if fn is not None:
            kind, conf = fn(cls, score, w, h)
            if kind:
                return kind, conf, d
        else:
            if cls in ("fall", "caduta"):
                return "fall", max(0.7, score), d
            if cls in ("immobility", "immobilita", "immobilità"):
                return "immobility", max(0.65, score), d
            if (cls in ("person", "persona")) and h > 0 and w / h >= 1.6 and score >= 0.75:
                return "fall", score, d
    return None, 0.0, {}
