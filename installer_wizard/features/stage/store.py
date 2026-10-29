import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import threading
import time
import unicodedata
from collections import OrderedDict
from pathlib import Path

from config import STATE_DIR
from features.stage import native, particles

log = logging.getLogger("nuxiva.stage")

ROOT = Path(os.environ.get("NUXIVA_PARTICLES_DIR", str(STATE_DIR / "particles")))
DIGEST = re.compile(r"^[0-9a-f]{64}$")
MAX_CONCEPTS = 2_000
CACHE_BYTES = 48 * 1024 * 1024


def concept_key(text: str) -> str:
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()[:60]


class _PyCache:
    def __init__(self, budget: int) -> None:
        self.budget, self.used, self.items = budget, 0, OrderedDict()

    def get(self, key: str):
        blob = self.items.get(key)
        if blob is not None:
            self.items.move_to_end(key)
        return blob

    def put(self, key: str, blob: bytes) -> bool:
        if not DIGEST.match(key) or len(blob) > self.budget:
            return False
        old = self.items.pop(key, None)
        if old is not None:
            self.used -= len(old)
        while self.items and self.used + len(blob) > self.budget:
            _, dropped = self.items.popitem(last=False)
            self.used -= len(dropped)
        self.items[key] = blob
        self.used += len(blob)
        return True

    def __len__(self) -> int:
        return len(self.items)


class ParticleStore:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.lock = threading.RLock()
        self.index: dict[str, dict] = {}
        self.loaded = False
        self.cache = native.lib.RustParticleCache(CACHE_BYTES) if native.lib is not None else _PyCache(CACHE_BYTES)

    def _ensure(self) -> None:
        if self.loaded:
            return
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.root / "blobs").mkdir(exist_ok=True, mode=0o700)
        self.index = self._read_index()
        self.loaded = True

    def _key(self) -> bytes:
        path = self.root / ".key"
        try:
            data = path.read_bytes()
            if len(data) == 32:
                return data
        except FileNotFoundError:
            pass
        data = secrets.token_bytes(32)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        return data

    def _sign(self, payload: bytes) -> str:
        return hmac.new(self._key(), payload, hashlib.sha256).hexdigest()

    def _read_index(self) -> dict:
        path = self.root / "index.json"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            payload = json.dumps(doc.get("concepts", {}), sort_keys=True, separators=(",", ":")).encode()
            if not hmac.compare_digest(str(doc.get("sig", "")), self._sign(payload)):
                log.warning("Indice delle particelle non firmato correttamente: lo ricostruisco")
                return {}
            concepts = doc.get("concepts", {})
            return {k: v for k, v in concepts.items() if isinstance(v, dict) and DIGEST.match(str(v.get("digest", "")))}
        except FileNotFoundError:
            return {}
        except (OSError, ValueError, AttributeError) as exc:
            log.warning("Indice delle particelle non leggibile (%s)", type(exc).__name__)
            return {}

    def _write_index(self) -> None:
        payload = json.dumps(self.index, sort_keys=True, separators=(",", ":")).encode()
        doc = json.dumps({"concepts": self.index, "sig": self._sign(payload)}, ensure_ascii=False)
        tmp = self.root / "index.json.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(doc)
        os.replace(tmp, self.root / "index.json")

    def lookup(self, concept: str) -> dict | None:
        key = concept_key(concept)
        with self.lock:
            self._ensure()
            hit = self.index.get(key)
            if hit and self.blob(hit["digest"]) is not None:
                hit["uses"] = int(hit.get("uses", 0)) + 1
                hit["last"] = time.time()
                return {"concept": key, **hit}
            return None

    def put(self, concept: str, spec: dict, blob: bytes) -> dict:
        key = concept_key(concept)
        if not key:
            raise particles.ParticleError("empty concept")
        particles.count(blob)
        digest = hashlib.sha256(blob).hexdigest()
        with self.lock:
            self._ensure()
            path = self.root / "blobs" / f"{digest}.nxpc"
            if not path.exists():
                tmp = path.with_suffix(".tmp")
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "wb") as fh:
                    fh.write(blob)
                os.replace(tmp, path)
            self.index[key] = {"digest": digest, "spec": particles.validate(spec), "created": time.time(), "uses": 1,
                               "last": time.time()}
            if len(self.index) > MAX_CONCEPTS:
                for old in sorted(self.index, key=lambda k: self.index[k].get("last", 0))[:len(self.index) - MAX_CONCEPTS]:
                    self.index.pop(old, None)
            self._write_index()
            self.cache.put(digest, blob)
            return {"concept": key, **self.index[key]}

    def blob(self, digest: str) -> bytes | None:
        if not DIGEST.match(str(digest)):
            return None
        cached = self.cache.get(digest)
        if cached is not None:
            return bytes(cached)
        path = self.root / "blobs" / f"{digest}.nxpc"
        try:
            data = path.read_bytes()
        except OSError:
            return None
        if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), digest):
            log.warning("Animazione a particelle corrotta scartata: %s", digest[:12])
            return None
        try:
            particles.count(data)
        except particles.ParticleError:
            return None
        self.cache.put(digest, data)
        return data

    def listing(self) -> list[dict]:
        with self.lock:
            self._ensure()
            return [{"concept": k, "digest": v["digest"], "uses": v.get("uses", 0), "created": v.get("created", 0)}
                    for k, v in sorted(self.index.items(), key=lambda kv: -kv[1].get("last", 0))]


store = ParticleStore()
