import unicodedata

STOPWORDS = frozenset({
    "a", "ad", "al", "alla", "alle", "agli", "ai", "che", "chi", "con", "da", "dal", "dalla",
    "dei", "del", "della", "delle", "degli", "di", "e", "ed", "gli", "il", "in", "la", "le", "lo",
    "mi", "ne", "nei", "nel", "nella", "o", "per", "si", "su", "sul", "sulla", "ti", "tra", "fra",
    "un", "una", "uno", "the", "an", "and", "or", "of", "to", "for", "on", "at", "by", "with",
    "from", "is", "are", "be", "it", "its", "me", "my", "you", "your", "les", "des", "du", "au",
    "aux", "et", "ou", "pour", "sur", "avec", "dans", "une", "el", "los", "las", "y", "para",
    "por", "sus", "mis",
})

FOLD = str.maketrans({
    "à": "a", "á": "a", "â": "a", "ã": "a", "ä": "a", "å": "a", "æ": "a", "ç": "c",
    "è": "e", "é": "e", "ê": "e", "ë": "e", "ì": "i", "í": "i", "î": "i", "ï": "i",
    "ñ": "n", "ò": "o", "ó": "o", "ô": "o", "õ": "o", "ö": "o", "ø": "o", "ù": "u",
    "ú": "u", "û": "u", "ü": "u", "ý": "y", "ÿ": "y", "œ": "o", "ß": "s",
})

_NOT_SPACE = frozenset("\x1c\x1d\x1e\x1f")


def trim(text: str) -> str:
    start, end = 0, len(text)
    while start < end and text[start].isspace() and text[start] not in _NOT_SPACE:
        start += 1
    while end > start and text[end - 1].isspace() and text[end - 1] not in _NOT_SPACE:
        end -= 1
    return text[start:end]


def normalize(text: str) -> str:
    out: list[str] = []
    space = True
    for raw in text:
        for c in raw.lower().translate(FOLD):
            if c.isalnum():
                out.append(c)
                space = False
            elif not space:
                out.append(" ")
                space = True
    if out and out[-1] == " ":
        out.pop()
    return "".join(out)


def tokens(text: str) -> list[str]:
    return [w for w in normalize(text).split(" ") if len(w) >= 3 and w not in STOPWORDS]


def has_control(text: str) -> bool:
    return any(unicodedata.category(c) == "Cc" and c not in "\n\t" for c in text)
