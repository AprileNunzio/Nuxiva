import html
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

from features.team.stopwords import clean_tokens

SKIP = {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "iframe"}
BLOCK = {"p", "h1", "h2", "h3", "li", "article", "section", "div", "br", "tr"}
META_DATES = (
    re.compile(r'<meta[^>]+(?:property|name|itemprop)=["\'](?:article:published_time|og:article:published_time|datePublished|date|pubdate|publishdate|DC\.date\.issued)["\'][^>]*content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name|itemprop)=["\'](?:article:published_time|datePublished|date)["\']', re.I),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)', re.I),
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"'),
)
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý0-9«\"])")
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.depth += 1
        elif tag in BLOCK and not self.depth:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIP and self.depth:
            self.depth -= 1
        elif tag in BLOCK and not self.depth:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.depth:
            self.parts.append(data)


def readable(markup: str) -> str:
    parser = _Text()
    try:
        parser.feed(markup)
        parser.close()
    except (AssertionError, ValueError):
        pass
    lines = (re.sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).split("\n"))
    return "\n".join(line for line in lines if len(line) > 40)


def title_of(markup: str) -> str:
    found = TITLE.search(markup)
    return re.sub(r"\s+", " ", html.unescape(found.group(1))).strip()[:160] if found else ""


def parse_date(value: str) -> float | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    stamp = parsed.timestamp()
    return stamp if 0 < stamp <= datetime.now(timezone.utc).timestamp() + 86400 else None


def published_of(markup: str, header: str = "") -> float | None:
    head = markup[:200_000]
    for pattern in META_DATES:
        for match in pattern.finditer(head):
            stamp = parse_date(match.group(1))
            if stamp:
                return stamp
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', head, re.I | re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            stamp = parse_date(str(item.get("datePublished", ""))) if isinstance(item, dict) else None
            if stamp:
                return stamp
    return parse_date(header)


def excerpt(text: str, question: str, limit: int = 600, sentences: int = 3) -> str:
    wanted = clean_tokens(question)
    candidates = [s.strip() for line in text.split("\n") for s in SENTENCE.split(line) if 30 <= len(s.strip()) <= 400]
    scored = [(len(wanted & clean_tokens(s)), index, s) for index, s in enumerate(candidates)]
    best = sorted((item for item in scored if item[0] > 0), key=lambda item: (-item[0], item[1]))[:sentences]
    chosen = [s for _, _, s in sorted(best, key=lambda item: item[1])]
    return " ".join(chosen)[:limit]
