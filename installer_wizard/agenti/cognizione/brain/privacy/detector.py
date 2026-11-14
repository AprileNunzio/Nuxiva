import re
import threading
from typing import Iterable

import native_core

from agenti.brain.privacy.levels import PERSONAL, PUBLIC, SENSITIVE, strictest

MAX_SCAN = 20_000
_SENSITIVE = (
    re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,4})?\b"),
    re.compile(r"\b[A-Z]{6}\d{2}[A-EHLMPR-T]\d{2}[A-Z]\d{3}[A-Z]\b", re.I),
    re.compile(r"\b(?:password|passcode|pin|otp|cvv|cvc|codice (?:segreto|di sicurezza|pin))\b", re.I),
    re.compile(r"\b(?:analisi del sangue|esami del sangue|emocromo|referto|referti|diagnosi|terapia|farmac[oi]|"
               r"prescrizione|ricetta medica|glicemia|colesterolo|trigliceridi|emoglobina|creatinina|"
               r"pressione arteriosa|ricovero|malattia|patologia|sintom[oi]|vaccin[oi]|gravidanza|"
               r"blood test|lab results?|diagnos[ie]s|medication|prescription|cholesterol|pregnan(?:t|cy)|"
               r"análisis de sangre|diagnóstico|receta médica|analyses? de sang|ordonnance)\b", re.I),
)
_PERSONAL = (
    re.compile(r"\b[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63})+\b"),
    re.compile(r"(?<![\w+])(?:\+\d{1,3}[\s.-]?\d|[03]\d)(?:[\s.-]?\d){7,10}(?!\d)"),
    re.compile(r"\b(?:mia moglie|mio marito|mio figlio|mia figlia|mio padre|mia madre|mio fratello|mia sorella|"
               r"la mia compagna|il mio compagno|abito (?:a|in)|il mio indirizzo|stipendio|conto corrente|"
               r"my wife|my husband|my son|my daughter|my address|my salary|bank account)\b", re.I),
)
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")


def _luhn(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char) * (2 if index % 2 else 1)
        total += value - 9 if value > 9 else value
    return total % 10 == 0


def _card(text: str) -> bool:
    return any(_luhn(re.sub(r"\D", "", m.group(0))) for m in _CARD.finditer(text))


def _named(text: str, names: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(name)}\b", lowered) for name in names if len(name) >= 3)


def classify(text: object, names: Iterable[str] = ()) -> str:
    body = str(text or "")[:MAX_SCAN]
    if not body.strip():
        return PUBLIC
    if _card(body) or any(rx.search(body) for rx in _SENSITIVE):
        return SENSITIVE
    if any(rx.search(body) for rx in _PERSONAL) or _named(body, names):
        return PERSONAL
    return PUBLIC


_native = None
_lock = threading.Lock()


def _engine():
    global _native
    if _native is None:
        with _lock:
            if _native is None:
                factory = native_core.symbol("RustPrivacy")
                _native = factory() if factory is not None else False
    return _native or None


def _py_classify_all(texts: Iterable[object], names: Iterable[str] = ()) -> str:
    known = tuple(names)
    return strictest(*(classify(text, known) for text in texts))


def classify_all(texts: Iterable[object], names: Iterable[str] = ()) -> str:
    items = tuple(texts)
    known = tuple(names)
    engine = _engine()
    if engine is None:
        native_core.python_fallback("brain.privacy")
        return _py_classify_all(items, known)
    try:
        kind, level = engine.classify_all([str(text or "") for text in items], [str(name) for name in known])
    except ValueError:
        return _py_classify_all(items, known)
    return _py_classify_all(items, known) if kind == "defer" else level
