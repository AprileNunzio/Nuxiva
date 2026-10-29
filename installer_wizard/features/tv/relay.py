import base64
import hashlib
import hmac
import ipaddress
import io
import re
import urllib.parse
import xml.etree.ElementTree as ET

import httpx

from features.music import tokens

PLAYLIST_LIMIT = 2 * 1024 * 1024
TOKEN_TTL = 12 * 3600
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
CORS = {"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"}
_URI_ATTR = re.compile(r'URI="([^"]+)"')
HLS_TYPES = ("mpegurl", "x-mpegurl", "vnd.apple.mpegurl")
DASH_TYPE = "application/dash+xml"
DASH_NS = "urn:mpeg:dash:schema:mpd:2011"
XLINK_NS = "http://www.w3.org/1999/xlink"
_DECLARATION = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)", re.I)
_PACKED = re.compile(r"^[A-Za-z0-9_-]{4,1400}\.[a-f0-9]{24}$")
_SEGMENT_ATTRS = {
    "SegmentTemplate": ("media", "initialization", "index"),
    "SegmentURL": ("media", "index"),
    "Initialization": ("sourceURL",),
    "RepresentationIndex": ("sourceURL",),
}
_DROPPED = ("PatchLocation",)
_PATH_SAFE = "/$:@!&'()*+,;=-._~"


class RelayError(RuntimeError):
    pass


def token_for(cid: str) -> str:
    return tokens.sign("tv", cid, TOKEN_TTL)


def valid(cid: str, token: str) -> bool:
    return tokens.verify("tv", cid, token)


def _sig(cid: str, url: str) -> str:
    return hmac.new(tokens.secret(), f"seg|{cid}|{url}".encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def encode(cid: str, url: str, token: str) -> str:
    packed = base64.urlsafe_b64encode(url.encode("utf-8")).decode().rstrip("=")
    return f"/api/tv/seg/{cid}?u={packed}&s={_sig(cid, url)}&t={urllib.parse.quote(token)}"


def decode(cid: str, packed: str, sig: str) -> str:
    try:
        url = base64.urlsafe_b64decode(packed + "=" * (-len(packed) % 4)).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise RelayError("Segmento non valido") from exc
    if not hmac.compare_digest(_sig(cid, url), str(sig)):
        raise RelayError("Segmento non firmato")
    return url


def _origin(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise RelayError("Origine non valida")
    return f"{parts.scheme}://{parts.netloc}"


def _dash_sig(cid: str, origin: str) -> str:
    return hmac.new(tokens.secret(), f"dash|{cid}|{origin}".encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def dash_prefix(cid: str, origin: str, token: str) -> str:
    packed = base64.urlsafe_b64encode(origin.encode("utf-8")).decode().rstrip("=")
    return f"/api/tv/dash/{cid}/{urllib.parse.quote(token, safe='')}/{packed}.{_dash_sig(cid, origin)}"


def dash_url(cid: str, url: str, token: str, origin: str) -> str | None:
    if not allowed(origin, url):
        return None
    try:
        source = _origin(url)
    except RelayError:
        return None
    parts = urllib.parse.urlsplit(url)
    return dash_prefix(cid, source, token) + (parts.path or "/") + (f"?{parts.query}" if parts.query else "")


def dash_target(cid: str, base: str, rest: str, query: str = "") -> str:
    if not _PACKED.match(base or ""):
        raise RelayError("Base DASH non valida")
    packed, sig = base.rsplit(".", 1)
    try:
        origin = base64.urlsafe_b64decode(packed + "=" * (-len(packed) % 4)).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise RelayError("Base DASH non valida") from exc
    if not hmac.compare_digest(_dash_sig(cid, origin), sig) or _origin(origin) != origin:
        raise RelayError("Base DASH non firmata")
    if len(rest) > 4000 or len(query) > 4000 or any(c in rest for c in "\\\x00\r\n\t") or any(c in query for c in "\x00\r\n\t"):
        raise RelayError("Segmento DASH non valido")
    target = f"{origin}/{urllib.parse.quote(rest.lstrip('/'), safe=_PATH_SAFE)}"
    if query:
        target += f"?{query}"
    if _origin(target) != origin:
        raise RelayError("Segmento DASH non ammesso")
    return target


def is_dash(url: str, content_type: str) -> bool:
    return urllib.parse.urlsplit(url).path.lower().endswith(".mpd") or "dash+xml" in content_type.lower()


def _local(tag) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _parse_dash(text: str) -> ET.Element:
    if _DECLARATION.search(text):
        raise RelayError("manifest DASH con dichiarazioni non ammesse")
    spaces: dict[str, str] = {}
    try:
        for event, item in ET.iterparse(io.BytesIO(text.encode("utf-8")), events=("start-ns", "end")):
            if event == "start-ns":
                spaces.setdefault(item[0], item[1])
            else:
                root = item
    except ET.ParseError as exc:
        raise RelayError("manifest DASH non valido") from exc
    if _local(root.tag) != "MPD":
        raise RelayError("manifest DASH non valido")
    for prefix, uri in spaces.items():
        if not re.fullmatch(r"ns\d+", prefix):
            ET.register_namespace(prefix, uri)
    return root


def _absolute(value: str) -> bool:
    return value.startswith("/") or urllib.parse.urlsplit(value).scheme in ("http", "https")


def rewrite_dash(text: str, base: str, cid: str, token: str, origin: str) -> str:
    root = _parse_dash(text)
    ns = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else ""
    qualified = (lambda name: f"{{{ns}}}{name}") if ns else (lambda name: name)

    def proxy(target: str) -> str:
        return encode(cid, target, token) if allowed(origin, target) else ""

    def walk(node: ET.Element, upstream: str) -> None:
        current = upstream
        bases = [child for child in node if _local(child.tag) == "BaseURL"]
        kept = False
        for child in bases:
            target = urllib.parse.urljoin(upstream, (child.text or "").strip())
            local = dash_url(cid, target, token, origin)
            if local is None:
                node.remove(child)
                continue
            child.text = local
            if not kept:
                current, kept = target, True
        for child in list(node):
            name = _local(child.tag)
            if name in _DROPPED:
                node.remove(child)
                continue
            if name == "Location":
                child.text = proxy(urllib.parse.urljoin(base, (child.text or "").strip()))
                if not child.text:
                    node.remove(child)
                continue
            if name == "UTCTiming" and "http" in child.get("schemeIdUri", ""):
                links = [proxy(urllib.parse.urljoin(base, v)) for v in child.get("value", "").split()]
                child.set("value", " ".join(v for v in links if v))
            href = f"{{{XLINK_NS}}}href"
            if child.get(href) and _absolute(child.get(href)):
                child.set(href, proxy(urllib.parse.urljoin(current, child.get(href))))
            for attr in _SEGMENT_ATTRS.get(name, ()):
                value = child.get(attr)
                if value and _absolute(value):
                    child.set(attr, dash_url(cid, urllib.parse.urljoin(current, value), token, origin) or "")
            if name != "BaseURL":
                walk(child, current)

    if not any(_local(child.tag) == "BaseURL" for child in root):
        anchor = ET.Element(qualified("BaseURL"))
        anchor.text = urllib.parse.urljoin(base, ".")
        anchor.tail = "\n"
        root.insert(0, anchor)
    walk(root, base)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def internal(url: str) -> bool:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host in ("localhost",) or host.endswith((".local", ".internal", ".lan")):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def allowed(origin: str, url: str) -> bool:
    scheme = urllib.parse.urlsplit(url).scheme
    return scheme in ("http", "https") and (not internal(url) or internal(origin))


def is_playlist(url: str, content_type: str) -> bool:
    path = urllib.parse.urlsplit(url).path.lower()
    return path.endswith((".m3u8", ".m3u")) or any(t in content_type.lower() for t in HLS_TYPES)


def rewrite(text: str, base: str, cid: str, token: str, origin: str) -> str:
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            def swap(m):
                target = urllib.parse.urljoin(base, m.group(1))
                return f'URI="{encode(cid, target, token)}"' if allowed(origin, target) else 'URI=""'
            out.append(_URI_ATTR.sub(swap, line))
        elif stripped:
            target = urllib.parse.urljoin(base, stripped)
            out.append(encode(cid, target, token) if allowed(origin, target) else "#rimosso")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


_RANGE = re.compile(r"^bytes=\d{0,15}-\d{0,15}$")
PASS_HEADERS = ("content-range", "content-length", "accept-ranges", "content-encoding")


def range_header(value: str | None) -> dict:
    return {"Range": value} if value and _RANGE.match(value) else {}


async def open_upstream(url: str, extra: dict | None = None) -> tuple[httpx.AsyncClient, httpx.Response]:
    client = httpx.AsyncClient(timeout=httpx.Timeout(20, read=30), follow_redirects=True, headers=HEADERS)
    try:
        res = await client.send(client.build_request("GET", url, headers=extra or {}), stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise RelayError(f"sorgente non raggiungibile ({type(exc).__name__})") from exc
    if res.status_code >= 400:
        await res.aclose()
        await client.aclose()
        raise RelayError(f"la sorgente ha risposto {res.status_code}")
    return client, res


async def read_playlist(res: httpx.Response) -> str:
    chunks, size = [], 0
    async for chunk in res.aiter_bytes():
        size += len(chunk)
        if size > PLAYLIST_LIMIT:
            raise RelayError("playlist del canale troppo grande")
        chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")
