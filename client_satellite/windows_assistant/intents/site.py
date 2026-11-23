import re
from dataclasses import dataclass
from urllib.parse import urlsplit

MAX_TEXT = 300
MAX_URL = 2048
VERB = re.compile(
    r"^\s*(?:ehi\s+\w+[,\s]+|hey\s+\w+[,\s]+)?(?:per favore\s+|please\s+)?"
    r"(?:apri|aprimi|apra|aprire|vai su|vai a|portami su|portami a|naviga su|mostrami|"
    r"open|go to|navigate to|take me to|show me|ouvre|ouvre-moi|va sur|aller sur|abre|ábreme|abreme|ve a|ir a)\b", re.I)
SITE_WORD = re.compile(r"\b(?:sito|site|website|sitio|pagina web|page web|página web|web)\b", re.I)
TOKEN = re.compile(r"(?<![\w@./\\:-])((?:https?://)?(?:www\.)?(?:[^\W_][\w-]{0,62}\.)+[^\W\d_]{2,24}(?::\d{1,5})?"
                   r"(?:/[^\s\"'<>`]*)?)(?![\w@-])", re.I)
BROWSERS = (
    ("chrome", re.compile(r"\b(?:google\s+)?chrome\b", re.I)),
    ("edge", re.compile(r"\b(?:microsoft\s+)?edge\b", re.I)),
    ("firefox", re.compile(r"\b(?:mozilla\s+)?firefox\b", re.I)),
    ("brave", re.compile(r"\bbrave\b", re.I)),
    ("opera", re.compile(r"\bopera\b", re.I)),
)
COMMON_TLD = frozenset({
    "com", "it", "net", "org", "io", "dev", "eu", "fr", "es", "de", "uk", "co", "app", "ai", "info", "biz", "me",
    "tv", "ch", "at", "be", "nl", "us", "ca", "au", "pt", "pl", "se", "no", "dk", "fi", "ie", "gr", "ro", "cz",
    "hu", "sk", "si", "hr", "ru", "jp", "cn", "in", "br", "mx", "ar", "cl", "tech", "online", "site", "store",
    "shop", "cloud", "blog", "news", "xyz", "gov", "edu", "int", "mil", "page", "website", "studio", "agency",
})
FILE_EXT = frozenset({
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "pdf", "txt", "md", "csv", "json", "xml", "html", "htm", "css",
    "js", "ts", "py", "rs", "java", "exe", "msi", "bat", "cmd", "ps1", "zip", "rar", "png", "jpg", "jpeg", "gif",
    "svg", "mp3", "mp4", "wav", "avi", "mov", "dwg", "dxf", "pln", "skp", "lsp", "scr", "log", "ini", "cfg", "yaml",
    "yml", "toml", "sql", "db", "odt", "ods", "rtf",
})


@dataclass(frozen=True)
class SiteIntent:
    url: str
    host: str
    browser: str


def _browser(text: str) -> str:
    return next((name for name, pattern in BROWSERS if pattern.search(text)), "")


def _host_ok(host: str) -> bool:
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return False
    labels = ascii_host.split(".")
    return len(ascii_host) <= 253 and len(labels) >= 2 and all(
        0 < len(label) <= 63 and not label.startswith("-") and not label.endswith("-") for label in labels)


def _url(token: str, explicit_site: bool) -> tuple[str, str] | None:
    has_scheme = token.lower().startswith(("http://", "https://"))
    candidate = token if has_scheme else f"https://{token}"
    candidate = candidate.rstrip(".,;:!?)]}")
    if len(candidate) > MAX_URL or "\\" in candidate:
        return None
    try:
        parts = urlsplit(candidate)
        _ = parts.port
    except ValueError:
        return None
    host = (parts.hostname or "").rstrip(".")
    if parts.scheme not in ("http", "https") or not host or parts.username or parts.password or not _host_ok(host):
        return None
    tld = host.rsplit(".", 1)[-1].lower()
    trusted_shape = has_scheme or host.lower().startswith("www.")
    if not trusted_shape and tld in FILE_EXT:
        return None
    if not (trusted_shape or explicit_site or tld in COMMON_TLD):
        return None
    return candidate, host


def parse(text: str) -> SiteIntent | None:
    raw = (text or "").strip()
    if not raw or len(raw) > MAX_TEXT or not VERB.search(raw):
        return None
    tokens = TOKEN.findall(raw)
    if len(tokens) != 1:
        return None
    resolved = _url(tokens[0], bool(SITE_WORD.search(raw)))
    if resolved is None:
        return None
    url, host = resolved
    return SiteIntent(url=url, host=host, browser=_browser(raw.replace(tokens[0], " ")))
