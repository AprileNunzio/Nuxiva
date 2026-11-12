"""
Filtro stopwords e normalizzatore semantico enterprise multilingue per Nuxiva.
Fornisce insiemi esaustivi di stopwords per le principali lingue mondiali
(Italiano, Inglese, Spagnolo, Francese, Tedesco, Portoghese) e rilevatori
deterministici per saluti, convenevoli e richieste di identità, azzerando i falsi positivi
nel routing degli agenti e dei widget su qualsiasi lingua ricevuta.
"""

import re

# Espressione regolare per estrazione token
TOKEN_RE = re.compile(r"[a-z0-9_-]{2,}", re.IGNORECASE)

# Stopwords esaustive in Italiano
ITALIAN_STOPWORDS: frozenset[str] = frozenset({
    "il", "lo", "la", "i", "gli", "le", "l",
    "un", "uno", "una", "un'",
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "del", "dello", "della", "dei", "degli", "delle",
    "al", "allo", "alla", "ai", "agli", "alle",
    "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "nel", "nello", "nella", "nei", "negli", "nelle",
    "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "col", "coi", "pel", "pei",
    "io", "tu", "lui", "lei", "noi", "voi", "loro", "esso", "essa", "essi", "esse",
    "me", "te", "se", "ne", "ci", "vi", "ti", "mi", "si", "li", "le",
    "questo", "questa", "questi", "queste", "quest",
    "quello", "quella", "quelli", "quelle", "quel", "quell",
    "chi", "che", "cui", "quale", "quali", "quanto", "quanti", "quanta", "quante",
    "cosa", "cose", "qualche", "alcuni", "alcune", "alcuno", "alcuna",
    "mio", "mia", "miei", "mie", "tuo", "tua", "tuoi", "tue",
    "suo", "sua", "suoi", "sue", "nostro", "nostra", "nostri", "nostre",
    "vostro", "vostra", "vostri", "vostre",
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

# Stopwords in Spagnolo
SPANISH_STOPWORDS: frozenset[str] = frozenset({
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "a", "al", "en", "con", "por", "para", "sobre", "entre", "tras", "sin",
    "como", "cómo", "cuando", "cuándo", "donde", "dónde", "porque", "por qué",
    "que", "qué", "quien", "quién", "cual", "cuál", "cuales", "cuáles", "cuanto", "cuánto",
    "pero", "mas", "y", "e", "o", "u", "ni", "si", "sino",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "aquel", "aquella",
    "mi", "mis", "tu", "tus", "su", "sus", "nuestro", "nuestra", "vuestro", "vuestra",
    "yo", "tú", "él", "ella", "ello", "nosotros", "vosotros", "ellos", "ellas", "usted", "ustedes",
    "me", "te", "se", "nos", "os", "lo", "la", "le", "los", "las", "les",
    "muy", "mucho", "mucha", "muchos", "muchas", "poco", "poca", "pocos", "pocas",
    "todo", "toda", "todos", "todas", "otro", "otra", "otros", "otras",
    "ser", "estar", "haber", "hacer", "decir", "ir", "poder", "tener",
    "soy", "eres", "es", "somos", "sois", "son", "era", "eras", "éramos", "eran", "fui", "fue",
    "estoy", "estás", "está", "estamos", "estáis", "están",
    "he", "has", "ha", "hemos", "habéis", "han", "había",
    "hago", "haces", "hace", "hacemos", "hacéis", "hacen",
    "puedo", "puedes", "puede", "podemos", "podéis", "pueden",
    "tengo", "tienes", "tiene", "tenemos", "tenéis", "tienen",
    "voy", "vas", "va", "vamos", "vais", "van",
    "hola", "buenos días", "buenas tardes", "buenas noches", "gracias", "por favor"
})

# Stopwords in Francese
FRENCH_STOPWORDS: frozenset[str] = frozenset({
    "le", "la", "les", "l'", "un", "une", "des", "du", "de", "d'",
    "à", "au", "aux", "en", "dans", "par", "pour", "sur", "sous", "avec", "sans", "chez",
    "comme", "comment", "quand", "lorsque", "où", "ou", "et", "mais", "donc", "car", "ni",
    "que", "qui", "quoi", "dont", "lequel", "laquelle", "lesquels", "lesquelles",
    "ce", "cet", "cette", "ces", "ceci", "cela", "ça",
    "mon", "ma", "mes", "ton", "ta", "tes", "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur", "leurs",
    "je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles",
    "me", "te", "se", "lui", "leur", "y", "en",
    "être", "avoir", "faire", "dire", "aller", "pouvoir", "vouloir", "devoir",
    "suis", "es", "est", "sommes", "êtes", "sont", "étais", "était", "étions", "étiez", "étaient", "été",
    "ai", "as", "a", "avons", "avez", "ont", "avais", "avait", "avions", "aviez", "avaient", "eu",
    "fais", "fait", "faisons", "faites", "font",
    "peux", "peut", "pouvons", "pouvez", "peuvent",
    "veux", "veut", "voulons", "voulez", "veulent",
    "dois", "doit", "devons", "devez", "doivent",
    "vais", "vas", "va", "allons", "allez", "vont",
    "bonjour", "bonsoir", "salut", "merci", "s'il vous plaît", "s'il te plaît"
})

# Stopwords in Tedesco
GERMAN_STOPWORDS: frozenset[str] = frozenset({
    "der", "die", "das", "den", "dem", "des",
    "ein", "eine", "einer", "eines", "einem", "einen",
    "in", "an", "auf", "aus", "bei", "mit", "nach", "von", "zu", "über", "unter", "vor", "zwischen",
    "durch", "für", "ohne", "um", "gegen",
    "wie", "wenn", "wann", "wo", "warum", "wer", "was", "welche", "welcher", "welches", "welchen", "welchem",
    "und", "oder", "aber", "denn", "doch", "sondern",
    "nicht", "kein", "keine", "keiner", "keines", "keinem", "keinen",
    "dieser", "diese", "dieses", "diesen", "diesem", "jeder", "jede", "jedes",
    "mein", "meine", "dein", "deine", "sein", "seine", "ihr", "ihre", "unser", "unsere", "euer", "eure",
    "ich", "du", "er", "sie", "es", "wir", "ihr", "sie", "Sie",
    "mich", "dich", "ihn", "uns", "euch", "mir", "dir", "ihm", "ihnen",
    "sein", "haben", "werden", "können", "müssen", "wollen", "sollen",
    "bin", "bist", "ist", "sind", "war", "waren", "gewesen",
    "habe", "hast", "hat", "haben", "hatte", "hatten", "gehabt",
    "kann", "kannst", "können", "muss", "musst", "müssen", "will", "willst", "wollen",
    "hallo", "guten morgen", "guten tag", "guten abend", "gute nacht", "danke", "bitte"
})

# Stopwords in Portoghese
PORTUGUESE_STOPWORDS: frozenset[str] = frozenset({
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas", "por", "pelo", "pela", "pelos", "pelas",
    "para", "com", "sem", "sob", "sobre", "entre", "até",
    "como", "quando", "onde", "porque", "por que", "que", "quem", "qual", "quais", "quanto", "quantos",
    "mas", "e", "ou", "nem", "se", "senão",
    "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas", "aquele", "aquela",
    "meu", "minha", "meus", "minhas", "teu", "tua", "teus", "tuas", "seu", "sua", "seus", "suas",
    "nosso", "nossa", "nossos", "nossas",
    "eu", "tu", "ele", "ela", "nós", "vós", "eles", "elas", "você", "vocês",
    "me", "te", "se", "nos", "vos", "o", "a", "lhe", "os", "as", "lhes",
    "muito", "muita", "muitos", "muitas", "pouco", "pouca", "poucos", "poucas", "tudo", "todos", "todas",
    "ser", "estar", "ter", "haver", "fazer", "dizer", "ir", "poder",
    "sou", "és", "é", "somos", "sois", "são", "era", "fui", "foi", "sido",
    "estou", "estás", "está", "estamos", "estais", "estão",
    "tenho", "tens", "tem", "temos", "tendes", "têm", "tinha", "tive",
    "posso", "podes", "pode", "podemos", "podeis", "podem",
    "faço", "fazes", "faz", "fazemos", "fazeis", "fazem",
    "olá", "bom dia", "boa tarde", "boa noite", "obrigado", "obrigada", "por favor"
})

ALL_STOPWORDS: frozenset[str] = (
    ITALIAN_STOPWORDS | ENGLISH_STOPWORDS | SPANISH_STOPWORDS |
    FRENCH_STOPWORDS | GERMAN_STOPWORDS | PORTUGUESE_STOPWORDS
)

# Pattern multilingue per saluti, convenevoli e general conversation
GREETING_PATTERN = re.compile(
    r"^(ciao|buongiorno|buond[iì]|buonasera|buonanotte|salve|hey|ehi"
    r"|hello|hi|good morning|good evening|good afternoon"
    r"|hola|buenos d[ií]as|buenas tardes|buenas noches"
    r"|bonjour|bonsoir|salut"
    r"|hallo|guten morgen|guten tag|guten abend"
    r"|ol[aá]|bom dia|boa tarde|boa noite)"
    r"(\s+(nuxiva|assistente|amico|tutti|a tutti|assistant|friend))?"
    r"([\s,!.?]+(come\s+va|come\s+stai|tutto\s+bene|come\s+butta"
    r"|how\s+are\s+you|what's\s+up|how\s+is\s+it\s+going"
    r"|c[oó]mo\s+est[aá]s|c[oó]mo\s+te\s+va|qu[eé]\s+tal|todo\s+bien"
    r"|comment\s+[cç]a\s+va|comment\s+vas-tu|tout\s+va\s+bien"
    r"|wie\s+geht\s+es\s+dir|wie\s+geht's|alles\s+gut"
    r"|tudo\s+bem|como\s+vai))?[\s.?!]*$",
    re.IGNORECASE
)

SMALLTALK_PATTERN = re.compile(
    r"^(come\s+va|come\s+stai|tutto\s+bene|come\s+vanno\s+le\s+cose"
    r"|how\s+are\s+you|how\s+is\s+it\s+going|what's\s+up"
    r"|c[oó]mo\s+est[aá]s|c[oó]mo\s+te\s+va|qu[eé]\s+tal|todo\s+bien"
    r"|comment\s+[cç]a\s+va|comment\s+vas-tu|tout\s+va\s+bien"
    r"|wie\s+geht\s+es\s+dir|wie\s+geht's|alles\s+gut"
    r"|tudo\s+bem|como\s+vai)"
    r"(\s+(oggi|ora|adesso|today|now|hoy|ahora|aujourd'hui|maintenant|heute|jetzt|hoje|agora))?[\s.?!]*$",
    re.IGNORECASE
)

# Pattern multilingue per richieste di identità, scopo e capacità generali dell'assistente
IDENTITY_PATTERN = re.compile(
    r"^(chi\s+sei|come\s+ti\s+chiami|qual\s+[eè]\s+il\s+tuo\s+nome|qual\s+[eè]\s+la\s+tua\s+funzione"
    r"|presentati|raccontami\s+di\s+te|cosa\s+sai\s+fare|cosa\s+puoi\s+fare|cosa\s+fai"
    r"|who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do|introduce\s+yourself"
    r"|qui[eé]n\s+eres|c[oó]mo\s+te\s+llamas|qu[eé]\s+puedes\s+hacer|qu[eé]\s+sabes\s+hacer|pres[eé]ntate"
    r"|qui\s+es-tu|comment\s+t'appelles-tu|que\s+peux-tu\s+faire|pr[eé]sente-toi"
    r"|wer\s+bist\s+du|wie\s+hei[sß]t\s+du|was\s+kannst\s+du\s+tun|stelle\s+dich\s+vor"
    r"|quem\s+[eé]\s+voc[eê]|como\s+voc[eê]\s+se\s+chama|o\s+que\s+voc[eê]\s+pode\s+fazer|apresente-se)[\s.?!]*$",
    re.IGNORECASE
)


def normalize_text(text: str) -> str:
    """Normalizza testo rimuovendo caratteri speciali e uniformando a minuscolo."""
    if not text:
        return ""
    cleaned = text.replace("’", "'").replace("`", "'")
    return cleaned.strip().lower()


def is_conversational_query(text: str) -> bool:
    """
    Rileva se la richiesta è una tipica interazione conversazionale generica
    (saluti, convenevoli, convenzioni sociali o richieste d'identità) in qualsiasi lingua supportata.
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
    Estrae solo i token semantici significativi (non-stopwords) con lunghezza >= 3,
    filtrando le stopwords delle principali lingue internazionali.
    """
    clean = normalize_text(text)
    words = TOKEN_RE.findall(clean)
    result: set[str] = set()
    for w in words:
        if len(w) >= 3 and w not in ALL_STOPWORDS:
            result.add(w)
    return result
