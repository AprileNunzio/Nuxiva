import html
import json
import re
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, quote_plus, urlencode, urlsplit
from xml.etree import ElementTree

from config import env_get

from features.research import safeweb

DDG = "https://html.duckduckgo.com/html/"
NEWS = "https://news.google.com/rss/search"
RESULT = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=<a[^>]+class="result__a"|\Z)', re.S)
SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)
TAGS = re.compile(r"<[^>]+>")
DATE_FILTER = ((1, "d"), (7, "w"), (31, "m"), (366, "y"))


@dataclass(frozen=True, slots=True)
class Hit:
    title: str
    url: str
    snippet: str
    source: str
    published: float | None
    via: str


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAGS.sub(" ", value))).strip()


def unwrap(href: str) -> str:
    target = parse_qs(urlsplit(html.unescape(href)).query).get("uddg")
    if target:
        return target[0]
    return "https:" + href if href.startswith("//") else href


def recency_code(days: int) -> str:
    return next((code for limit, code in DATE_FILTER if 0 < days <= limit), "")


async def duckduckgo(query: str, language: str, days: int) -> list[Hit]:
    params = {"q": query, "kl": f"{language}-{language}"}
    if recency_code(days):
        params["df"] = recency_code(days)
    page = await safeweb.fetch(f"{DDG}?{urlencode(params)}")
    hits = []
    for href, title, rest in RESULT.findall(page.text):
        url = unwrap(href)
        found = SNIPPET.search(rest)
        if url.startswith("http") and "duckduckgo.com" not in urlsplit(url).netloc:
            hits.append(Hit(plain(title), url, plain(found.group(1)) if found else "", urlsplit(url).netloc.lower(), None, "web"))
    return hits


async def news(query: str, language: str, days: int) -> list[Hit]:
    window = f"+when:{max(1, days)}d" if days > 0 else ""
    url = f"{NEWS}?q={quote_plus(query)}{window}&hl={language}&gl={language.upper()}&ceid={language.upper()}:{language}"
    page = await safeweb.fetch(url)
    if "<!DOCTYPE" in page.text or "<!ENTITY" in page.text:
        raise safeweb.WebError("bad_type")
    try:
        root = ElementTree.fromstring(page.text)
    except ElementTree.ParseError:
        raise safeweb.WebError("bad_type")
    hits = []
    for item in root.iter("item"):
        source = item.find("source")
        published = None
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "").timestamp()
        except (TypeError, ValueError):
            published = None
        host = urlsplit(source.get("url", "")).netloc.lower() if source is not None else ""
        title = plain(item.findtext("title") or "")
        if title and host:
            hits.append(Hit(title, source.get("url", ""), "", host, published, "news"))
    return hits[:15]


async def searxng(query: str, language: str, days: int) -> list[Hit]:
    base = env_get("NUXIVA_SEARXNG_URL", "").strip().rstrip("/")
    if not base:
        return []
    params = {"q": query, "format": "json", "language": language}
    if recency_code(days):
        params["time_range"] = {"d": "day", "w": "week", "m": "month", "y": "year"}[recency_code(days)]
    page = await safeweb.fetch(f"{base}/search?{urlencode(params)}")
    try:
        rows = json.loads(page.text).get("results", [])
    except ValueError:
        raise safeweb.WebError("bad_type")
    hits = []
    for row in rows[:15]:
        url = str(row.get("url", ""))
        if url.startswith("http"):
            hits.append(Hit(plain(str(row.get("title", ""))), url, plain(str(row.get("content", ""))), urlsplit(url).netloc.lower(), None, "web"))
    return hits
