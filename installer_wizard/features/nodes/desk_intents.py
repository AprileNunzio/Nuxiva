import re
from urllib.parse import urlsplit

OPEN_URL = re.compile(r"^(?:apri|aprimi|open|ouvre|abre)\s+(https?://[^\s<>]+)$", re.IGNORECASE)
RESEARCH_REQUEST = re.compile(
    r"^(?:cerca (?:online|sul web|su internet)|search (?:online|the web)|cherche (?:en ligne|sur internet)|"
    r"busca (?:en línea|en internet))(?:\s*[:：]\s*|\s+)(.+)$", re.IGNORECASE)


def browser_target(text: str) -> str:
    match = OPEN_URL.fullmatch(text)
    if not match or "\\" in match[1]:
        return ""
    try:
        url = urlsplit(match[1])
        if not url.hostname or url.username is not None or url.password is not None:
            return ""
        _ = url.port
    except ValueError:
        return ""
    return match[1]
