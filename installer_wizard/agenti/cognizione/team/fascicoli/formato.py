import unicodedata

SCHEMA = "nuxiva.fascicolo/1"
REQUIRED_KEYS = ("schema", "file", "operazione", "livello", "autore", "creato")
MAX_KEY, MAX_VALUE, MAX_KEYS = 32, 512, 32
MAX_HEADING, MAX_SECTION, MAX_SECTIONS, MAX_DOC = 160, 64 * 1024, 64, 256 * 1024
SECTIONS = {
    "richiesta": ("request", "origin"),
    "contesto": ("agents", "signals"),
    "piano": ("goal", "criteria", "steps", "risks"),
    "passo": ("goal", "tool", "result", "check", "status"),
    "verifica": ("criteria", "evidence", "verdict"),
    "esito": ("summary", "answer", "timing"),
}
FIXED = {"richiesta": "00-richiesta.md", "contesto": "01-contesto.md", "piano": "02-piano.md",
         "verifica": "90-verifica.md", "esito": "99-esito.md"}
LEVELS = {
    "lampo": ("richiesta", "esito"),
    "standard": ("richiesta", "contesto", "piano", "esito"),
    "progetto": ("richiesta", "contesto", "piano", "passo", "verifica", "esito"),
}


class Problem(ValueError):
    def __init__(self, at: str, code: str) -> None:
        super().__init__(code)
        self.at, self.code = at, code

    def as_dict(self) -> dict:
        return {"at": self.at, "code": self.code}


def _control(c: str) -> bool:
    return unicodedata.category(c) == "Cc"


def valid_key(key: str) -> bool:
    return 0 < len(key) <= MAX_KEY and all("a" <= c <= "z" or c == "_" for c in key)


def line(text: str, limit: int) -> str:
    flat = "".join(" " if _control(c) else c for c in text)
    return flat.strip()[:limit]


def body(text: str) -> str:
    clean = "".join(c for c in text if c in "\n\t" or not _control(c))
    return clean.replace("<!--", "&lt;!--").strip("\n")[:MAX_SECTION]


def sanitize(doc: dict) -> dict:
    front = [(k, v) for k, v in doc.get("front", []) if valid_key(k)][:MAX_KEYS]
    sections = [s for s in doc.get("sections", []) if valid_key(s.get("anchor", ""))][:MAX_SECTIONS]
    return {
        "front": [[k, line(v, MAX_VALUE)] for k, v in front],
        "title": line(doc.get("title", ""), MAX_HEADING),
        "sections": [{"anchor": s["anchor"], "heading": line(s.get("heading", ""), MAX_HEADING), "body": body(s.get("body", ""))}
                     for s in sections],
    }


def render(doc: dict) -> str:
    doc = sanitize(doc)
    out = ["---\n"]
    out += [f"{k}: {v}\n" for k, v in doc["front"]]
    out.append(f"---\n\n# {doc['title']}\n")
    for s in doc["sections"]:
        out.append(f"\n<!-- s:{s['anchor']} -->\n## {s['heading']}\n")
        if s["body"]:
            out.append(s["body"] + "\n")
    return "".join(out)


def _rust_lines(text: str) -> list[str]:
    if not text:
        return []
    parts = text.split("\n")
    if text.endswith("\n"):
        parts.pop()
    return [p[:-1] if p.endswith("\r") else p for p in parts]


def _anchor(raw: str) -> str | None:
    if raw.startswith("<!-- s:") and raw.endswith(" -->") and len(raw) >= 11:
        anchor = raw[7:-4]
        return anchor if valid_key(anchor) else None
    return None


def parse(text: str) -> dict:
    if len(text.encode("utf-8")) > MAX_DOC:
        raise Problem("", "too_large")
    if not text.startswith("---\n"):
        raise Problem("", "no_front")
    rest = text[4:]
    if rest.startswith("---\n"):
        front_text, rest = "", rest[4:]
    else:
        at = rest.find("\n---\n")
        if at < 0:
            raise Problem("", "no_front_end")
        front_text, rest = rest[:at], rest[at + 5:]
    front = []
    for raw in _rust_lines(front_text):
        key, sep, value = raw.partition(": ")
        if not sep:
            raise Problem("front", "bad_line")
        if not valid_key(key):
            raise Problem("front", "bad_key")
        front.append([key, value])
    if not rest.startswith("\n# "):
        raise Problem("", "no_title")
    lines = rest[3:].split("\n")
    title, sections, current, expect = lines[0], [], None, False
    for raw in lines[1:]:
        if expect:
            if not raw.startswith("## "):
                raise Problem("section", "no_heading")
            current["heading"], expect = raw[3:], False
            continue
        anchor = _anchor(raw)
        if anchor is not None:
            if current is not None:
                current["body"] = current["body"].strip("\n")
                sections.append(current)
            current, expect = {"anchor": anchor, "heading": "", "body": ""}, True
            continue
        if current is not None:
            current["body"] += raw + "\n"
        elif raw:
            raise Problem("", "text_outside_section")
    if expect:
        raise Problem("section", "no_heading")
    if current is not None:
        current["body"] = current["body"].strip("\n")
        sections.append(current)
    return {"front": front, "title": title, "sections": sections}


def get(doc: dict, key: str) -> str | None:
    return next((v for k, v in doc["front"] if k == key), None)


def validate(doc: dict, kind: str) -> list[dict]:
    out = []
    for key in REQUIRED_KEYS:
        if not get(doc, key):
            out.append({"at": key, "code": "missing"})
    if get(doc, "schema") not in (None, SCHEMA):
        out.append({"at": "schema", "code": "unknown_schema"})
    if get(doc, "file") not in (None, kind):
        out.append({"at": "file", "code": "wrong_kind"})
    if get(doc, "livello") is not None and get(doc, "livello") not in LEVELS:
        out.append({"at": "livello", "code": "unknown_level"})
    seen: list[str] = []
    for s in doc["sections"]:
        if s["anchor"] in seen:
            out.append({"at": s["anchor"], "code": "duplicate"})
        seen.append(s["anchor"])
    for anchor in SECTIONS[kind]:
        if anchor not in seen:
            out.append({"at": anchor, "code": "missing_section"})
    if not doc["title"].strip():
        out.append({"at": "title", "code": "missing"})
    return out


def _step_name(name: str) -> bool:
    if not name.endswith(".md"):
        return False
    number, _, slug = name[:-3].partition("-")
    return (len(number) == 2 and number.isascii() and number.isdigit() and number != "00" and 0 < len(slug) <= 48
            and all(c.isascii() and (c.islower() or c.isdigit() or c == "-") for c in slug)
            and not slug.startswith("-") and not slug.endswith("-"))


def kind_of_name(name: str) -> str | None:
    if name.startswith("passi/"):
        return "passo" if _step_name(name[6:]) else None
    return next((k for k, v in FIXED.items() if v == name), None)


def step_file(number: int, slug: str) -> str | None:
    clean = "".join(c if c.isascii() and c.isalnum() else "-" for c in slug.lower())
    compact = "-".join(p for p in clean.split("-") if p)[:48].rstrip("-")
    if not 1 <= number <= 99 or not compact:
        return None
    return f"passi/{number:02d}-{compact}.md"
