import json
import logging
import secrets
import threading

from agenti.nvr import catalog_py, nvm2
from agenti.nvr.vault import MediaVault, _private_write
import native_module

log = logging.getLogger("nuxiva.nvr.catalog")
CONTEXT = "nvr.catalog.v1"
FILE_NAME = ".catalog.nvb"


def engine_class():
    cls = native_module.feature("RustNvrCatalog")
    if cls is None:
        native_module.python_fallback("nvr.catalog")
        return catalog_py.PyNvrCatalog
    return cls


def next_marker(markers: list[dict], at_ms: int, forward: bool, kinds: list[str]) -> dict | None:
    fn = native_module.feature("nvr_next_marker") or catalog_py.next_marker
    found = fn(json.dumps(markers, separators=(",", ":")), int(at_ms), bool(forward), list(kinds))
    return json.loads(found) if found else None


def _vault_engine(vault: MediaVault):
    cls = native_module.feature("RustMediaVault")
    return cls(vault._master_key()) if cls is not None and hasattr(cls, "seal_blob") else None


class Catalog:
    def __init__(self, vault: MediaVault) -> None:
        self.vault = vault
        self.lock = threading.RLock()
        self._inner = None
        self.dirty = False

    @property
    def path(self):
        return self.vault.root / FILE_NAME

    @property
    def inner(self):
        with self.lock:
            if self._inner is None:
                self._inner = self._load()
            return self._inner

    def _load(self):
        cls = engine_class()
        if self.path.exists():
            try:
                blob = self.path.read_bytes()
                engine = _vault_engine(self.vault)
                plain = bytes(engine.open_blob(CONTEXT, blob)) if engine is not None \
                    else nvm2.py_open_blob(self.vault._master_key(), CONTEXT, blob)
                return cls.from_json(plain.decode("utf-8"))
            except (OSError, ValueError) as exc:
                log.warning("NVR: catalogo illeggibile, lo ricostruisco dai segmenti: %s", exc)
        return self._rebuild(cls())

    def _rebuild(self, fresh):
        if not self.vault.root.exists():
            return fresh
        for path in sorted(self.vault.root.glob("*/*.nvm")):
            try:
                row = self.row_from_header(path)
            except (OSError, ValueError) as exc:
                log.warning("NVR: segmento %s scartato dal catalogo: %s", path.name, exc)
                continue
            if row:
                fresh.insert(json.dumps(row))
        self.dirty = True
        return fresh

    def row_from_header(self, path) -> dict | None:
        info = self.vault.header(path)
        if info is None:
            return None
        return {"id": info["segment_id"], "camera": info["camera_id"], "start_ms": info["recorded_at_ms"],
                "duration_ms": max(1, info["duration_ms"]), "bytes": info["file_bytes"], "tier": info["tier"],
                "audio": info["has_audio"], "video": info["has_video"]}

    def save(self) -> None:
        with self.lock:
            if not self.dirty or self._inner is None:
                return
            plain = self._inner.to_json().encode("utf-8")
            nonce = secrets.token_bytes(nvm2.NONCE_LEN)
            engine = _vault_engine(self.vault)
            blob = bytes(engine.seal_blob(CONTEXT, nonce, plain)) if engine is not None \
                else nvm2.py_seal_blob(self.vault._master_key(), CONTEXT, nonce, plain)
            _private_write(self.path, blob)
            self.dirty = False

    def add(self, row: dict) -> None:
        with self.lock:
            self.inner.insert(json.dumps(row))
            self.dirty = True

    def remove(self, camera: str, segment_id: str) -> dict | None:
        with self.lock:
            gone = self.inner.remove(camera, segment_id)
            self.dirty = self.dirty or gone is not None
            return json.loads(gone) if gone else None

    def set_tier(self, camera: str, segment_id: str, tier: str) -> None:
        with self.lock:
            self.inner.set_tier(camera, segment_id, tier)
            self.dirty = True

    def get(self, camera: str, segment_id: str) -> dict | None:
        found = self.inner.get(camera, segment_id)
        return json.loads(found) if found else None

    def range(self, camera: str, from_ms: int, to_ms: int, limit: int = 2000) -> list[dict]:
        return json.loads(self.inner.range(camera, int(from_ms), int(to_ms), int(limit)))

    def seek(self, camera: str, at_ms: int) -> dict | None:
        found = self.inner.seek(camera, int(at_ms))
        return json.loads(found) if found else None

    def after(self, camera: str, segment_id: str) -> dict | None:
        found = self.inner.after(camera, segment_id)
        return json.loads(found) if found else None

    def spans(self, camera: str, from_ms: int, to_ms: int, tolerance_ms: int = 3000) -> list[dict]:
        return json.loads(self.inner.spans(camera, int(from_ms), int(to_ms), int(tolerance_ms)))

    def summary(self) -> list[dict]:
        return json.loads(self.inner.summary())

    def total_bytes(self) -> int:
        return int(self.inner.total_bytes())

    def plan(self, policy: dict, events: list[tuple[str, int]], now_ms: int) -> dict:
        return json.loads(self.inner.plan(json.dumps(policy), json.dumps([[c, int(t)] for c, t in events]), int(now_ms)))
