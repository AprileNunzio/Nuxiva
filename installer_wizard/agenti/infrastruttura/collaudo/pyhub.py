import hashlib
import hmac
import json
import math
import re
import secrets
import threading
import time
from pathlib import Path

DOMAINS = frozenset({"sentinel", "ear", "vision", "supervisor", "worker", "mcp", "error", "resource", "probe", "system"})
LEVELS = ("trace", "debug", "info", "warn", "error")
DENIED = ("name", "nome", "voice", "voce", "face", "volto", "allerg", "email", "mail", "phone", "telefono", "address",
          "indirizzo", "passw", "secret", "token", "apikey", "api_key", "transcript", "trascri", "utterance", "frase",
          "prompt", "body", "text", "speech", "embedding", "vector", "biometric", "health", "salute", "diagnos",
          "medic", "birth", "nascita", "fiscal", "iban", "card", "cookie", "credential", "bearer")
TEXT_KEYS = ("msg", "error", "detail", "reason")
REDACTED = "[redatto]"
TOKEN = re.compile(r"[a-z0-9_.:\-]+")
HEX = re.compile(r"[0-9a-f]+")
EDGE = re.compile(r"^[^A-Za-z0-9@._\-+/=]+|[^A-Za-z0-9@._\-+/=]+$")
BLOB = re.compile(r"[A-Za-z0-9+/=\-_]+")
MAX_FIELDS, MAX_TEXT = 24, 160
RAW_KEYS = {"domain", "level", "kind", "corr", "src", "fields", "at_ms"}


def is_token(value: str, limit: int) -> bool:
    return 0 < len(value) <= limit and TOKEN.fullmatch(value) is not None


def is_hex(value: str, low: int, high: int) -> bool:
    return low <= len(value) <= high and HEX.fullmatch(value) is not None


def _digit(c: str) -> bool:
    return "0" <= c <= "9"


def scrub_text(value: str) -> str:
    flat = [" " if ord(c) < 32 or 127 <= ord(c) < 160 else c for c in value]
    out: list[str] = []
    i = 0
    while i < len(flat):
        c = flat[i]
        if c == "/":
            rest = "".join(flat[i:i + 8])
            prefix = "/home/" if rest.startswith("/home/") else "/Users/" if rest.startswith("/Users/") else ""
            if prefix:
                out.append(prefix + "~")
                i += len(prefix)
                while i < len(flat) and flat[i] not in "/ \"'":
                    i += 1
                continue
        if _digit(c) or c == "+":
            end = i
            while end < len(flat) and (_digit(flat[end]) or flat[end] in "- .+"):
                end += 1
            while end > i + 1 and not _digit(flat[end - 1]):
                end -= 1
            if sum(1 for x in flat[i:end] if _digit(x)) >= 7:
                out.append(REDACTED)
                i = end
                continue
        out.append(c)
        i += 1
    words = []
    for word in "".join(out).split(" "):
        bare = EDGE.sub("", word)
        email = "@" in bare and "." in bare
        hexblob = len(bare) >= 24 and re.fullmatch(r"[0-9a-fA-F]+", bare) is not None
        longblob = len(bare) >= 32 and BLOB.fullmatch(bare) is not None
        words.append(REDACTED if email or hexblob or longblob else word)
    return " ".join(words)[:MAX_TEXT]


class PyHub:
    def __init__(self, directory: Path, key_hex: str, segment_bytes: int, keep: int) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.key = bytes.fromhex(key_hex)
        self.segment_bytes = max(4096, segment_bytes)
        self.keep = max(1, keep)
        self.lock = threading.Lock()
        self.mode = False
        self.counts = {"emitted": 0, "dropped_verbose": 0, "dropped_rate": 0, "rejected": 0}
        self.seq = self._last_seq() + 1

    def _segments(self) -> list[Path]:
        return sorted(self.dir.glob("seg-*.jsonl"))

    def _last_seq(self) -> int:
        segments = self._segments()
        if not segments:
            return 0
        last = 0
        for line in segments[-1].read_text(encoding="utf-8").splitlines():
            try:
                last = json.loads(line.split("\t", 1)[1])["seq"]
            except (IndexError, KeyError, ValueError):
                continue
        return last

    def _pseudonym(self, key: str, value: str) -> str:
        digest = hmac.new(self.key, f"nuxiva.collaudo.value:{key}\0{value}".encode(), hashlib.sha256).hexdigest()
        return "h:" + digest[:12]

    def _text(self, key: str, value: str, free: bool) -> tuple[str, bool]:
        if any(d in key for d in DENIED):
            return REDACTED, True
        if key.endswith("_ref"):
            return self._pseudonym(key, value), True
        if free and key in TEXT_KEYS:
            scrubbed = scrub_text(value)
            return scrubbed, scrubbed != value
        pii = "@" in value or sum(1 for c in value if _digit(c)) >= 7
        if is_token(value, 64) and not pii and not is_hex(value, 24, 10 ** 9):
            return value, False
        return self._pseudonym(key, value), True

    def _fields(self, raw: dict, free: bool) -> dict:
        out: dict = {}
        redacted = 0
        for key, value in raw.items():
            key = str(key).strip().lower()
            if len(out) >= MAX_FIELDS - 1 or not is_token(key, 32):
                redacted += 1
                continue
            if isinstance(value, str):
                value, changed = self._text(key, value, free)
                redacted += changed
            elif isinstance(value, float) and not math.isfinite(value):
                redacted += 1
                continue
            elif not isinstance(value, (bool, int, float)):
                redacted += 1
                continue
            out[key] = value
        if redacted:
            out["redacted_n"] = redacted
        return out

    def emit(self, raw: str):
        if len(raw) > 16 * 1024:
            raise ValueError("collaudo.invalid.size")
        data = json.loads(raw)
        if not isinstance(data, dict) or not RAW_KEYS.issuperset(data):
            raise ValueError("collaudo.invalid.json")
        domain, level, kind, src = data.get("domain"), data.get("level"), data.get("kind", ""), data.get("src", "")
        corr = data.get("corr")
        if domain not in DOMAINS or level not in LEVELS:
            raise ValueError("collaudo.invalid.json")
        if not is_token(kind, 64) or not is_token(src, 48) or (corr is not None and not is_hex(corr, 8, 32)):
            raise ValueError("collaudo.invalid.kind")
        fields = data.get("fields") or {}
        if not isinstance(fields, dict):
            raise ValueError("collaudo.invalid.fields")
        free = domain in ("error", "system") and LEVELS.index(level) >= 3
        clean = self._fields(fields, free)
        with self.lock:
            if LEVELS.index(level) <= 1 and not self.mode:
                self.counts["dropped_verbose"] += 1
                return None
            envelope = {"v": 1, "seq": self.seq, "id": secrets.token_hex(8), "at_ms": int(data.get("at_ms") or time.time() * 1000),
                        "domain": domain, "level": level, "kind": kind, "corr": corr, "src": src, "fields": clean}
            line = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False)
            segments = self._segments()
            target = segments[-1] if segments and segments[-1].stat().st_size < self.segment_bytes else self.dir / f"seg-{self.seq:016d}.jsonl"
            fresh = not target.exists()
            with target.open("a", encoding="utf-8") as handle:
                handle.write(f"-\t{line}\n")
            if fresh:
                target.chmod(0o600)
                for old in self._segments()[:-self.keep]:
                    old.unlink(missing_ok=True)
            self.counts["emitted"] += 1
            self.seq += 1
            return envelope["seq"]

    def query(self, args: str) -> str:
        a = json.loads(args or "{}")
        limit = min(int(a.get("limit") or 500), 5000)
        floor = ("trace", "debug", "info", "warn", "error")
        minimum = floor.index(a["min_level"]) if a.get("min_level") else 0
        out = []
        for segment in self._segments():
            for line in segment.read_text(encoding="utf-8").splitlines():
                try:
                    env = json.loads(line.split("\t", 1)[1])
                except (IndexError, ValueError):
                    continue
                if env["seq"] <= int(a.get("since_seq") or 0):
                    continue
                if a.get("domain") and env["domain"] != a["domain"]:
                    continue
                if LEVELS.index(env["level"]) < minimum:
                    continue
                if a.get("corr") and env.get("corr") != a["corr"]:
                    continue
                if a.get("kind_prefix") and not env["kind"].startswith(a["kind_prefix"]):
                    continue
                if a.get("from_ms") and env["at_ms"] < a["from_ms"] or a.get("to_ms") and env["at_ms"] > a["to_ms"]:
                    continue
                out.append(env)
                if len(out) >= limit:
                    return json.dumps(out)
        return json.dumps(out)

    def set_collaudo(self, enabled: bool) -> None:
        self.mode = bool(enabled)

    def collaudo(self) -> bool:
        return self.mode

    def stats(self) -> str:
        return json.dumps(self.counts)

    def verify(self) -> str:
        return json.dumps({"segments": len(self._segments()), "lines": 0, "ok": None, "anchored": False,
                           "broken_segment": None, "reason": "native_required"})

    def flush(self) -> None:
        return None

    def report(self, args: str, spec=None) -> str:
        raise RuntimeError("collaudo.native_required")
