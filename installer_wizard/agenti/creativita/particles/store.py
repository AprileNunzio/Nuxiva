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
from agenti.particles import codec as particles
from agenti.particles.archive import MAX_META, open_archive, shard
from agenti.stage import native

log = logging.getLogger("nuxiva.particles")

ROOT = Path(os.environ.get("NUXIVA_PARTICLES_DIR", str(STATE_DIR / "particles")))
DIGEST = re.compile(r"^[0-9a-f]{64}$")
GENERATION = 2
MAX_CONCEPTS = 2_000
MAX_ARCHIVE = 1_000_000
EVICT_EVERY = 500
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
        self.archive = None
        self.puts = 0
        self.cache = native.lib.RustParticleCache(CACHE_BYTES) if native.lib is not None else _PyCache(CACHE_BYTES)

    def _ensure(self) -> None:
        if self.loaded:
            return
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.root / "blobs").mkdir(exist_ok=True, mode=0o700)
        self.index = self._read_index()
        self.archive = open_archive(self.root / "creazioni.db")
        if self.archive.count() == 0:
            for key, row in self.index.items():
                self._record(key, row)
        self.loaded = True

    def _path(self, digest: str) -> Path:
        return self.root / "blobs" / f"{shard(digest)}.nxpc"

    def _seal(self, key: str, digest: str, spec: dict) -> str:
        body = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return self._sign(f"{key}\n{digest}\n{body}".encode())

    def _record(self, key: str, row: dict, tags: list[str] | None = None) -> None:
        spec = row.get("spec") or {}
        meta = json.dumps({"spec": spec, "sig": self._seal(key, row["digest"], spec)}, separators=(",", ":"), ensure_ascii=False)
        if len(meta.encode()) > MAX_META:
            spec = {}
            meta = json.dumps({"spec": spec, "sig": self._seal(key, row["digest"], spec)}, separators=(",", ":"))
        self.archive.put({"key": key, "digest": row["digest"], "kind": "particles", "tags": tags or [], "meta": meta},
                         int(float(row.get("last", time.time())) * 1000))

    def _restore(self, key: str) -> dict | None:
        found = self.archive.lookup(key, int(time.time() * 1000))
        if not found or self.blob(found["digest"]) is None:
            return None
        try:
            meta = json.loads(found["meta"])
            spec = meta["spec"]
            if not hmac.compare_digest(str(meta["sig"]), self._seal(key, found["digest"], spec)):
                log.warning("Riga dell'archivio delle creazioni non firmata correttamente: ignorata")
                return None
            spec = particles.validate(spec) if spec else {}
        except (ValueError, KeyError, TypeError, particles.ParticleError):
            return None
        row = {"digest": found["digest"], "spec": spec, "created": found["created"] / 1000, "uses": found["uses"], "last": time.time()}
        self.index[key] = row
        return row

    def search(self, query: str, limit: int = 10) -> list[dict]:
        with self.lock:
            self._ensure()
            return [hit for hit in self.archive.search(query, limit) if self.blob(hit["digest"]) is not None]

    def count(self) -> int:
        with self.lock:
            self._ensure()
            return self.archive.count()

    def _evict(self) -> None:
        if self.archive.count() <= MAX_ARCHIVE:
            return
        for digest in self.archive.evict(MAX_ARCHIVE):
            self._path(digest).unlink(missing_ok=True)
            (self.root / "blobs" / f"{digest}.nxpc").unlink(missing_ok=True)

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
            hit = self.index.get(key) or self._restore(key)
            if hit and self.blob(hit["digest"]) is not None:
                hit["uses"] = int(hit.get("uses", 0)) + 1
                hit["last"] = time.time()
                return {"concept": key, **hit}
            return None

    def put(self, concept: str, spec: dict, blob: bytes, tags: list[str] | None = None) -> dict:
        key = concept_key(concept)
        if not key:
            raise particles.ParticleError("empty concept")
        particles.count(blob)
        digest = hashlib.sha256(blob).hexdigest()
        with self.lock:
            self._ensure()
            path = self._path(digest)
            if not path.exists() and not (self.root / "blobs" / f"{digest}.nxpc").exists():
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                tmp = path.with_suffix(".tmp")
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "wb") as fh:
                    fh.write(blob)
                os.replace(tmp, path)
            self.index[key] = {"digest": digest, "spec": particles.validate(spec), "created": time.time(), "uses": 1,
                               "last": time.time(), "gen": GENERATION}
            if len(self.index) > MAX_CONCEPTS:
                for old in sorted(self.index, key=lambda k: self.index[k].get("last", 0))[:len(self.index) - MAX_CONCEPTS]:
                    self.index.pop(old, None)
            self._write_index()
            self._record(key, self.index[key], tags)
            self.puts += 1
            if self.puts % EVICT_EVERY == 0:
                self._evict()
            self.cache.put(digest, blob)
            return {"concept": key, **self.index[key]}

    def blob(self, digest: str) -> bytes | None:
        if not DIGEST.match(str(digest)):
            return None
        cached = self.cache.get(digest)
        if cached is not None:
            return bytes(cached)
        try:
            data = self._path(digest).read_bytes()
        except OSError:
            try:
                data = (self.root / "blobs" / f"{digest}.nxpc").read_bytes()
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
