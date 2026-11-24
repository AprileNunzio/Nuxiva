import re

MAX_TEXT = 300
NOUN = re.compile(r"(screen\s?-?shot|schermat[ae]|istantanea dello schermo|(?:cattura|foto)\s+(?:dello|allo|lo|di|dell[oa])?\s*schermo|"
                  r"capture\s+(?:d['’]\s?)?(?:é|e)cran|captura\s+(?:de\s+)?pantalla|print\s?screen)", re.I)
VERB = re.compile(r"\b(fai|fa'|fammi|faccia|fate|scatta|scattami|cattura|catturami|prendi|salva|salvami|registra|"
                  r"take|make|grab|capture|snap|save|fais|faites|prends|enregistre|haz|hazme|toma|saca|captura)\b", re.I)
QUESTION = re.compile(r"\b(come\s+si|come\s+faccio|how\s+(?:do|to|can)|comment\s+(?:faire|on)|c[oó]mo\s+(?:se|hago)|"
                      r"perch[eé]|why|pourquoi|por\s*qu[eé])\b", re.I)


def asks(text: str) -> bool:
    text = (text or "").strip()
    if not text or len(text) > MAX_TEXT or QUESTION.search(text):
        return False
    noun = NOUN.search(text)
    if not noun:
        return False
    return noun.start() == 0 or bool(VERB.search(text))
