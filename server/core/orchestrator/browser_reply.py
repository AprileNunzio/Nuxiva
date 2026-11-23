import re

DOMAIN = re.compile(r"(?<![\w@./\\:-])((?:https?://)?(?:www\.)?(?:[^\W_][\w-]{0,62}\.)+[^\W\d_]{2,24}(?:/[^\s\"'<>`]*)?)"
                    r"(?![\w@-])", re.I)
PREFIX = re.compile(
    r"^\s*(?:per favore\s+)?(?:aprimi|apri|vai su|vai a|portami su|naviga su|cerca su|cercami|cerca|mostrami|open|"
    r"go to|search for|search)\s+(?:il sito(?: web)?(?: di)?|la pagina(?: web)?(?: di)?|the website|the site)?\s*",
    re.I)
BROWSER_TAIL = re.compile(
    r"\s+(?:su|con|in|nel|on|with)\s+(?:il\s+browser\s+)?(?:google\s+chrome|chrome|microsoft\s+edge|edge|"
    r"(?:mozilla\s+)?firefox|brave|opera|internet|google)\s*[.!?]*\s*$", re.I)


def browser_query(text: str) -> str:
    raw = (text or "").strip()
    domains = DOMAIN.findall(raw)
    if len(domains) == 1:
        return domains[0].rstrip(".,;:!?)]}")
    cleaned = BROWSER_TAIL.sub("", PREFIX.sub("", raw)).strip(" .!?")
    return cleaned or raw


def browser_speech(query: str, searched: bool) -> str:
    if searched:
        return f"Ho cercato sul web «{query}», signore."
    return f"Non sono riuscita a cercare «{query}» sul web, signore."
