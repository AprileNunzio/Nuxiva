import hashlib
import hmac
import json
import logging
import secrets
import threading
import time

from agenti.nvr import index_py, nvm2
from agenti.nvr.vault import _private_write
import native_module

log = logging.getLogger("nuxiva.nvr.index")
CONTEXT = "nvr.index.v1"
FILE_NAME = ".index.nvb"
SAVE_EVERY = 30.0


def index_key(master: bytes) -> bytes:
    prk = hmac.new(b"nuxiva.nvr.index.salt.v1", master[:32], hashlib.sha256).digest()
    return hmac.new(prk, b"blind-terms\x01", hashlib.sha256).digest()


def doc_prefix(camera: str, segment: str) -> str:
    return f"{camera}|{segment}|"


class SearchIndex:
    def __init__(self, vault, transcripts) -> None:
        self.vault = vault
        self.transcripts = transcripts
        self.lock = threading.RLock()
        self._inner = None
        self.dirty = False
        self.last_save = 0.0

    @property
    def path(self):
        return self.vault.root / FILE_NAME

    def _cls(self):
        cls = native_module.feature("RustNvrIndex")
        if cls is None:
            native_module.python_fallback("nvr.index")
            return index_py.PyNvrIndex
        return cls

    def _blob_engine(self):
        cls = native_module.feature("RustMediaVault")
        return cls(self.vault._master_key()) if cls is not None and hasattr(cls, "seal_blob") else None

    @property
    def inner(self):
        with self.lock:
            if self._inner is None:
                self._inner = self._load()
            return self._inner

    def _load(self):
        cls = self._cls()
        key = index_key(self.vault._master_key())
        if self.path.exists():
            try:
                blob = self.path.read_bytes()
                engine = self._blob_engine()
                plain = bytes(engine.open_blob(CONTEXT, blob)) if engine is not None \
                    else nvm2.py_open_blob(self.vault._master_key(), CONTEXT, blob)
                return cls.from_json(key, plain.decode("utf-8"))
            except (OSError, ValueError) as exc:
                log.warning("NVR: indice di ricerca illeggibile, lo ricostruisco: %s", exc)
        fresh = cls(key)
        root = self.transcripts.root
        for path in sorted(root.glob("*/*.nvb")) if root.exists() else []:
            try:
                data = self.transcripts.load(path.parent.name, path.stem)
            except (OSError, ValueError) as exc:
                log.warning("NVR: trascrizione %s esclusa dall'indice: %s", path.name, exc)
                continue
            self._add_turns(fresh, path.parent.name, path.stem, (data or {}).get("turns", []))
        self.dirty = True
        return fresh

    @staticmethod
    def _add_turns(engine, camera: str, segment: str, turns: list[dict]) -> None:
        for turn in turns:
            meta = {"key": f"{doc_prefix(camera, segment)}{int(turn['start_ms'])}", "camera": camera,
                    "at_ms": int(turn["start_ms"]), "kind": "speech"}
            text = f"{turn.get('text', '')} {turn.get('speaker') or ''}"[:15_000]
            engine.add(json.dumps(meta), text)

    def index_transcript(self, camera: str, segment: str, turns: list[dict]) -> None:
        with self.lock:
            self.inner.remove_prefix(doc_prefix(camera, segment))
            self._add_turns(self.inner, camera, segment, turns)
            self.dirty = True
        self.save()

    def forget(self, camera: str, segment: str) -> int:
        with self.lock:
            gone = int(self.inner.remove_prefix(doc_prefix(camera, segment)))
            self.dirty = self.dirty or gone > 0
        self.save()
        return gone

    def search(self, query: str, camera: str | None, from_ms: int, to_ms: int, limit: int = 50) -> list[dict]:
        with self.lock:
            return json.loads(self.inner.search(query[:300], camera, int(from_ms), int(to_ms), int(limit)))

    def save(self, force: bool = False) -> None:
        with self.lock:
            now = time.monotonic()
            if not self.dirty or self._inner is None or (not force and now - self.last_save < SAVE_EVERY):
                return
            plain = self._inner.to_json().encode("utf-8")
            nonce = secrets.token_bytes(nvm2.NONCE_LEN)
            engine = self._blob_engine()
            blob = bytes(engine.seal_blob(CONTEXT, nonce, plain)) if engine is not None \
                else nvm2.py_seal_blob(self.vault._master_key(), CONTEXT, nonce, plain)
            _private_write(self.path, blob)
            self.dirty = False
            self.last_save = now


def forget_derived(transcripts, index):
    def hook(camera: str, segment: str) -> None:
        transcripts.delete(camera, segment)
        index.forget(camera, segment)
    return hook


def _default():
    from agenti.nvr.archive import archive
    from agenti.nvr.transcripts import store
    built = SearchIndex(archive.vault, store)
    archive.listeners.append(forget_derived(store, built))
    return built


index = _default()
