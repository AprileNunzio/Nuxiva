import re
from pathlib import Path

from fastapi.responses import Response

from config import WEB_DIR
from pages import ASSET_VERSION

INDEX = WEB_DIR / "nexus" / "index.html"
_ASSET = re.compile(r'((?:src|href)="/static/nexus/[^"?]+)"')
TRUSTED_TYPE_POLICIES = (
    "editorViewLayer",
    "stickyScrollViewLayer",
    "editorGhostText",
    "domLineBreaksComputer",
    "diffEditorWidget",
    "diffReview",
    "richScreenReaderContent",
    "standaloneColorizer",
    "tokenizeToString",
    "defaultWorkerFactory",
    "nuxivaMonacoWorker",
    "dompurify",
)
CSP = "; ".join((
    "default-src 'none'",
    "script-src 'self'",
    "style-src 'self'",
    "style-src-elem 'self' 'unsafe-inline'",
    "style-src-attr 'unsafe-inline'",
    "img-src 'self' data: blob: https: http:",
    "font-src 'self'",
    "connect-src 'self' https: http: ws: wss:",
    "frame-src 'self' blob:",
    "media-src 'self' blob: https: http:",
    "manifest-src 'self'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    "require-trusted-types-for 'script'",
    "trusted-types " + " ".join(TRUSTED_TYPE_POLICIES),
))


def security_headers(https: bool) -> dict[str, str]:
    headers = {
        "Content-Security-Policy": CSP,
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), geolocation=(), payment=(), usb=(), microphone=(self)",
    }
    if https:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        headers["Cross-Origin-Opener-Policy"] = "same-origin"
        headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return headers


_LANG = re.compile(r"^[a-z]{2,3}$")


def render(https: bool, lang: str = "it") -> Response:
    dist_index = Path(__file__).resolve().parents[4] / "client_web" / "dist" / "index.html"
    if dist_index.is_file():
        html = dist_index.read_text(encoding="utf-8")
    elif INDEX.is_file():
        html = INDEX.read_text(encoding="utf-8")
    else:
        html = '<!DOCTYPE html><html lang="it"><head><meta charset="utf-8"><title>Nuxiva OS</title></head><body><div id="root"></div></body></html>'
    html = html.replace('<html lang="it">', f'<html lang="{lang if _LANG.match(lang or "") else "it"}">', 1)
    html = _ASSET.sub(lambda m: f'{m.group(1)}?v={ASSET_VERSION}"', html)
    return Response(html, media_type="text/html; charset=utf-8", headers=security_headers(https))
