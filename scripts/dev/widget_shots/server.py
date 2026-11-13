import json
import mimetypes
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WIZARD = ROOT / "installer_wizard"
sys.path[:0] = [str(WIZARD), str(WIZARD / "backend")]

from agenti._widgets import manifests
from agenti.desktop.manifest import normalize, TONES
from agenti.locale.colocated.api import resolver
from agenti.locale.colocated.domain import Locale, Scope
from config import UI_LANGUAGES, WIDGETS_DIR

WEB = WIZARD / "web"
SAMPLES = json.loads((HERE / "samples.json").read_text(encoding="utf-8"))
EPOCH = 1763000000


def shifted(value, delta):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and EPOCH - 100000 <= value <= EPOCH + 200000:
        return value + delta
    if isinstance(value, list):
        return [shifted(v, delta) for v in value]
    if isinstance(value, dict):
        return {k: shifted(v, delta) for k, v in value.items()}
    return value
FILES = {"widget.js", "widget.css"}


def catalog() -> dict[str, dict]:
    found = {}
    for path, owner in manifests(WIDGETS_DIR):
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("id", path.parent.name)
        normalize(data, path.parent, (WIDGETS_DIR,))
        data["owner"] = owner
        found[data["id"]] = data
    return found


def instances(ids: list[str]) -> list[dict]:
    items = catalog()
    chosen = [i for i in ids if i in items] or sorted(items)
    out = []
    for wid in chosen:
        m = items[wid]
        out.append({
            "id": wid, "key": f"shot:{wid}", "rev": m["rev"], "size": m["size"], "tone": m["tone"] if m["tone"] in TONES else "cyan",
            "css": m["has_css"], "chrome": m["chrome"], "essential": m["essential"], "urgent": m["urgent"],
            "simple": m.get("simple"), "data": shifted(SAMPLES.get(wid, {}), int(time.time()) - EPOCH), "name": m.get("name", wid), "owner": m["owner"],
        })
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status: int, body: bytes, kind: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def file(self, path: Path) -> None:
        if not path.is_file():
            self.send(404, b"nf", "text/plain")
            return
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send(200, path.read_bytes(), kind)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        parts = [p for p in url.path.split("/") if p]
        if url.path == "/harness":
            self.file(HERE / "harness.html")
        elif url.path == "/harness.js":
            self.file(HERE / "harness.js")
        elif url.path == "/instances.json":
            ids = [i for i in (q.get("ids", [""])[0]).split(",") if i]
            self.send(200, json.dumps(instances(ids), ensure_ascii=False).encode(), "application/json")
        elif parts[:1] == ["static"] and ".." not in parts:
            self.file(WEB.joinpath(*parts[1:]))
        elif len(parts) == 3 and parts[0] == "widgets" and parts[2] in FILES:
            found = {p.parent.name: p.parent for p, _ in manifests(WIDGETS_DIR)}
            self.file(found[parts[1]] / parts[2]) if parts[1] in found else self.send(404, b"nf", "text/plain")
        elif url.path == "/api/i18n/bundle":
            try:
                result = resolver.resolve(Scope.parse(q["scope"][0]), Locale.parse(q["locale"][0], frozenset(UI_LANGUAGES)))
                self.send(200, json.dumps(result.to_payload(), ensure_ascii=False).encode(), "application/json")
            except Exception:
                self.send(404, b"{}", "application/json")
        else:
            self.send(404, b"nf", "text/plain")


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
