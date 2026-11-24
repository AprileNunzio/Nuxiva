import re

SIMPLE_WORDS = 12
PATIENCE_RATIO = 0.35
PATIENCE_FLOOR_S = 0.4
DEEP = re.compile(
    r"\b(spiega\w*|confront\w*|analizz\w*|perch[eé]|dimostr\w*|progett\w*|pianific\w*|codice|script|calcola\w*|"
    r"explain\w*|compar\w*|analy[sz]\w*|why|prove|design\w*|plan\w*|code)\b",
    re.I,
)


def simple(query: str) -> bool:
    text = str(query or "")
    return len(text.split()) <= SIMPLE_WORDS and not DEEP.search(text)


def patience(wait_s: float, first_s: float) -> float:
    return max(0.0, min(float(wait_s), max(PATIENCE_FLOOR_S, float(first_s) * PATIENCE_RATIO)))
