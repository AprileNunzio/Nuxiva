import re
import unicodedata

DISTRESS_PATTERNS = {
    "help_words": (
        r"\b(aiuto|aiutatemi|soccorso|sto male|mi sento male|sono caduto|non riesco ad alzarmi|chiamate aiuto)\b",
        r"\b(help|help me|emergency|i fell|i need help|i cannot get up|call for help)\b",
        r"\b(ayuda|socorro|auxilio|me cai|me caí|estoy mal|no me puedo levantar)\b",
        r"\b(au secours|aidez moi|aidez-moi|je suis tombe|je suis tombé|je ne peux pas me lever)\b",
    ),
    "fire": (
        r"\b(al fuoco|sta bruciando|incendio|ce un incendio|c'è un incendio)\b",
        r"\b(fire|house on fire|building on fire|it is burning|it's burning)\b",
        r"\b(fuego|incendio|se esta quemando|se está quemando)\b",
        r"\b(au feu|ca brule|ça brûle|incendie)\b",
    ),
    "violence": (
        r"\b(lasciami|vattene|aiuto mi aggredisce|fermati)\b",
        r"\b(leave me alone|get away|stop attacking|don't touch me)\b",
        r"\b(dejame|vete|socorro me atacan|sueltame|suéltame)\b",
        r"\b(laissez-moi|au secours on m'agresse|arrete|arrête)\b",
    ),
}

ALL_CLEAR_PATTERNS = (
    r"\b(sto bene|tutto bene|tutto a posto|nessun problema|falso allarme|non e niente|non è niente)\b",
    r"\b(i am fine|i am ok|i'm fine|i'm ok|all good|false alarm|no problem|never mind)\b",
    r"\b(estoy bien|todo bien|falsa alarma|sin problema|no pasa nada)\b",
    r"\b(je vais bien|tout va bien|fausse alerte|pas de probleme|pas de problème|rien de grave)\b",
)

COMPILED_DISTRESS = {
    kind: [re.compile(p, re.IGNORECASE) for p in patterns]
    for kind, patterns in DISTRESS_PATTERNS.items()
}
COMPILED_ALL_CLEAR = [re.compile(p, re.IGNORECASE) for p in ALL_CLEAR_PATTERNS]


def normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    cleaned = "".join(c for c in normalized if not unicodedata.combining(c) or c in ("è", "é", "à", "ò", "ù", "ì"))
    return re.sub(r"\s+", " ", cleaned).strip()


def detect_speech_intent(text: str) -> tuple[str | None, float]:
    if not text or not isinstance(text, str):
        return None, 0.0
    norm = normalize_text(text)
    for pattern in COMPILED_ALL_CLEAR:
        if pattern.search(norm) or pattern.search(text):
            return "all_clear", 0.95
    for kind, patterns in COMPILED_DISTRESS.items():
        for pattern in patterns:
            if pattern.search(norm) or pattern.search(text):
                score = 0.95 if kind == "fire" else 0.90
                return kind, score
    return None, 0.0


def detect_visual_distress(detections: list[dict]) -> tuple[str | None, float, dict]:
    if not detections:
        return None, 0.0, {}
    for d in detections:
        cls = str(d.get("class") or "").lower()
        score = float(d.get("score", 0.0))
        if cls in ("fall", "caduta"):
            return "fall", max(0.7, score), d
        if cls in ("immobility", "immobilita", "immobilità"):
            return "immobility", max(0.65, score), d
        bbox = d.get("bbox") or d.get("box")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4 and cls in ("person", "persona"):
            w = float(bbox[2])
            h = float(bbox[3])
            if h > 0 and w / h >= 1.6 and score >= 0.75:
                return "fall", score, d
    return None, 0.0, {}
