"""
Filtro stopwords e normalizzatore semantico enterprise per Nuxiva.
Fornisce insiemi esaustivi di stopwords (italiano e inglese) e rilevatori
deterministici per saluti, convenevoli e richieste di identità dell'assistente,
azzerando i falsi positivi nel routing degli agenti e dei widget.
"""

import re

# Espressione regolare per estrazione token
TOKEN_RE = re.compile(r"[a-z0-9_-]{2,}", re.IGNORECASE)

# Stopwords esaustive in Italiano
ITALIAN_STOPWORDS: frozenset[str] = frozenset({
    # Articoli e determinativi
    "il", "lo", "la", "i", "gli", "le", "l",
    "un", "uno", "una", "un'",
    # Preposizioni semplici e articolate
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "del", "dello", "della", "dei", "degli", "delle",
    "al", "allo", "alla", "ai", "agli", "alle",
    "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "nel", "nello", "nella", "nei", "negli", "nelle",
    "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "col", "coi", "pel", "pei",
    # Pronomi personali, relativi e dimostrativi
    "io", "tu", "lui", "lei", "noi", "voi", "loro", "esso", "essa", "essi", "esse",
    "me", "te", "se", "ne", "ci", "vi", "ti", "mi", "si", "li", "le",
    "questo", "questa", "questi", "queste", "quest",
    "quello", "quella", "quelli", "quelle", "quel", "quell",
    "chi", "che", "cui", "quale", "quali", "quanto", "quanti", "quanta", "quante",
    "cosa", "cose", "qualche", "alcuni", "alcune", "alcuno", "alcuna",
    "mio", "mia", "miei", "mie", "tuo", "tua", "tuoi", "tue",
    "suo", "sua", "suoi", "sue", "nostro", "nostra", "nostri", "nostre",
    "vostro", "vostra", "vostri", "vostre",
    # Congiunzioni e avverbi comuni
    "e", "ed", "o", "od", "oppure", "ovvero", "ma", "però", "pero", "tuttavia",
    "quindi", "dunque", "perciò", "percio", "infatti", "invece",
    "se", "come", "dove", "quando", "mentre", "finché", "finche", "perché", "perche",
    "anche", "ancora", "pure", "neanche", "nemmeno", "neppure",
    "sempre", "mai", "spesso", "talvolta", "forse", "quasi", "circa",
    "bene", "male", "meglio", "peggio",
    "tutto", "tutti", "tutta", "tutte",
    "molto", "molti", "molta", "molte", "poco", "pochi", "poca", "poche",
    "più", "piu", "meno", "tanto", "tanti", "tanta", "tante",
    "così", "cosi", "allora", "dopo", "prima", "poi", "ora", "adesso", "subito",
    "qui", "qua", "lì", "li", "là", "la",
    "si", "sì", "no", "non", "niente", "nulla",
    # Verbi ausiliari e ad altissima frequenza (forme flesse)
    "essere", "avere", "fare", "dire", "andare", "potere", "volere", "dovere",
    "è", "e'", "sono", "sei", "siamo", "siete", "era", "erano", "ero", "eri",
    "sarà", "sara", "sarai", "sarò", "saro", "saremo", "sarete", "saranno",
    "stato", "stata", "stati", "state", "stai", "sta", "stiamo", "state", "stanno",
    "ho", "hai", "ha", "abbiamo", "avete", "hanno", "aveva", "avevano", "avevo",
    "avrà", "avra", "avrai", "avrò", "avro", "avremo", "avrete", "avranno",
    "avuto", "avuta", "avuti", "avute",
    "fai", "fa", "facciamo", "fate", "fanno", "fatto", "fatta", "fatti", "fatte",
    "dici", "dice", "diciamo", "dite", "dicono", "detto", "detta",
    "puoi", "può", "puo", "posso", "possiamo", "potete", "possono",
    "vuoi", "vuole", "voglio", "vogliamo", "volete", "vogliono",
    "devi", "deve", "devo", "dobbiamo", "dovete", "devono",
    "va", "vai", "andiamo", "andate", "vanno", "andato", "andata",
    # Riempitivi e interiezioni
    "beh", "boh", "mah", "ok", "okay", "va bene", "grazie", "prego", "scusa", "scusami",
    "per favore", "per cortesia", "dimmi", "ascolta", "senti"
})

# Stopwords in Inglese
ENGLISH_STOPWORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves", "tell", "please", "thanks", "thank"
})

ALL_STOPWORDS: frozenset[str] = ITALIAN_STOPWORDS | ENGLISH_STOPWORDS

# Pattern per saluti, convenevoli e general conversation
GREETING_PATTERN = re.compile(
    r"^(ciao|buongiorno|buond[iì]|buonasera|buonanotte|salve|hey|ehi|hello|hi|good morning|good evening)"
    r"(\s+(nuxiva|assistente|amico|tutti|a tutti))?"
    r"([\s,!.?]+(come\s+va|come\s+stai|tutto\s+bene|come\s+butta|how\s+are\s+you|what's\s+up))?[\s.?!]*$",
    re.IGNORECASE
)

SMALLTALK_PATTERN = re.compile(
    r"^(come\s+va|come\s+stai|tutto\s+bene|come\s+vanno\s+le\s+cose|how\s+are\s+you|how\s+is\s+it\s+going)"
    r"(\s+(oggi|ora|adesso|con\s+te))?[\s.?!]*$",
    re.IGNORECASE
)

# Pattern per richieste di identità, scopo e capacità generali dell'assistente
IDENTITY_PATTERN = re.compile(
    r"^(chi\s+sei|come\s+ti\s+chiami|qual\s+[eè]\s+il\s+tuo\s+nome|qual\s+[eè]\s+la\s+tua\s+funzione"
    r"|presentati|raccontami\s+di\s+te|cosa\s+sai\s+fare|cosa\s+puoi\s+fare|cosa\s+fai"
    r"|who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do)[\s.?!]*$",
    re.IGNORECASE
)


def normalize_text(text: str) -> str:
    """Normalizza testo rimuovendo accenti speciali e uniformando a minuscolo."""
    if not text:
        return ""
    # Sostituisce apostrofi vari con spazio o apostrofo standard
    cleaned = text.replace("’", "'").replace("`", "'")
    return cleaned.strip().lower()


def is_conversational_query(text: str) -> bool:
    """
    Rileva se la richiesta è una tipica interazione conversazionale generica
    (saluti, convenevoli, convenzioni sociali o richieste d'identità).
    """
    clean = normalize_text(text)
    if not clean:
        return True
    if GREETING_PATTERN.match(clean):
        return True
    if SMALLTALK_PATTERN.match(clean):
        return True
    if IDENTITY_PATTERN.match(clean):
        return True
    return False


def clean_tokens(text: str) -> set[str]:
    """
    Estrae solo i token semantici significativi (non-stopwords) con lunghezza >= 3.
    """
    clean = normalize_text(text)
    words = TOKEN_RE.findall(clean)
    result: set[str] = set()
    for w in words:
        if len(w) >= 3 and w not in ALL_STOPWORDS:
            result.add(w)
    return result
