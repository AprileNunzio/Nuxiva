import json
import logging
import os
import re
import secrets
import threading
import time
from collections import OrderedDict
from pathlib import Path

import native_module
from config import STATE_DIR

log = logging.getLogger("nuxiva.molecules")
ROOT = STATE_DIR / "molecules"
MAX_BYTES = 64 * 1024 * 1024
MAX_ITEMS = 200
CACHE_ITEMS = 8
FORMATS = {"pdb": "pdb", "ent": "pdb", "cif": "cif", "mmcif": "cif"}
LODS = frozenset({"atoms", "backbone"})
SCHEMES = frozenset({"element", "chain", "secondary"})
BACKBONE_ABOVE = 60_000
_ID = re.compile(r"^[0-9a-f]{16}$")
_TITLE = re.compile(r"[^\w .,:()+-]+", re.UNICODE)


class EngineUnavailable(RuntimeError):
    pass


def _engine():
    return native_module.feature("molecule_build")


def available() -> bool:
    return _engine() is not None


def clean_title(text) -> str:
    return " ".join(_TITLE.sub(" ", str(text or "")).split())[:80]


def format_of(name: str) -> str:
    fmt = FORMATS.get(Path(str(name)).suffix.lower().lstrip("."))
    if fmt is None:
        raise ValueError("molecule_unknown_format")
    return fmt


def folder(mid: str) -> Path:
    if not _ID.match(str(mid)):
        raise KeyError(mid)
    return ROOT / mid


def _write_private(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.replace(temporary, path)


class Library:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache: OrderedDict[tuple, tuple[dict, bytes]] = OrderedDict()

    @staticmethod
    def get(mid: str) -> dict:
        try:
            return json.loads((folder(mid) / "meta.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise KeyError(mid) from None

    @staticmethod
    def listing() -> list[dict]:
        if not ROOT.is_dir():
            return []
        items = []
        for path in ROOT.iterdir():
            meta = path / "meta.json"
            if _ID.match(path.name) and meta.is_file() and not path.is_symlink():
                try:
                    items.append(json.loads(meta.read_text(encoding="utf-8")))
                except (OSError, ValueError) as exc:
                    log.error("Scheda della molecola %s illeggibile: %s", path.name, exc)
        return sorted(items, key=lambda m: m.get("created", 0), reverse=True)

    def add(self, name: str, data: bytes, title: str = "") -> dict:
        fmt = format_of(name)
        if not data or len(data) > MAX_BYTES:
            raise ValueError("molecule_too_large")
        engine = _engine()
        if engine is None:
            raise EngineUnavailable("molecule_engine_unavailable")
        summary_json, _ = engine(data, fmt, "backbone", "element")
        summary = json.loads(summary_json)
        if len(self.listing()) >= MAX_ITEMS:
            raise ValueError("molecule_library_full")
        mid = secrets.token_hex(8)
        target = folder(mid)
        target.mkdir(parents=True, mode=0o700)
        _write_private(target / f"source.{fmt}", data)
        meta = {"id": mid, "title": clean_title(title) or clean_title(summary.get("title")) or clean_title(Path(name).stem),
                "format": fmt, "bytes": len(data), "atoms": summary["atoms"], "chains": summary["chains"][:64],
                "residues": summary["residues"], "helices": summary["helices"], "sheets": summary["sheets"],
                "created": time.time()}
        _write_private(target / "meta.json", json.dumps(meta).encode())
        return meta

    def remove(self, mid: str) -> None:
        target = folder(mid)
        if not target.is_dir() or target.is_symlink():
            raise KeyError(mid)
        for item in target.iterdir():
            item.unlink()
        target.rmdir()
        with self._lock:
            for key in [k for k in self._cache if k[0] == mid]:
                self._cache.pop(key)

    def default_lod(self, meta: dict) -> str:
        return "backbone" if int(meta.get("atoms", 0)) > BACKBONE_ABOVE else "atoms"

    def scene(self, mid: str, lod: str, scheme: str) -> tuple[dict, bytes]:
        if lod not in LODS or scheme not in SCHEMES:
            raise ValueError("molecule_bad_options")
        meta = self.get(mid)
        key = (mid, lod, scheme)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        engine = _engine()
        if engine is None:
            raise EngineUnavailable("molecule_engine_unavailable")
        source = folder(mid) / f"source.{meta['format']}"
        summary_json, packed = engine(source.read_bytes(), meta["format"], lod, scheme)
        result = (json.loads(summary_json), bytes(packed))
        with self._lock:
            self._cache[key] = result
            while len(self._cache) > CACHE_ITEMS:
                self._cache.popitem(last=False)
        return result

    def show(self, meta: dict) -> None:
        from features.desktop.desk import desk
        desk.hide("molecule_viewer")
        desk.show("molecule_viewer", {"id": meta["id"], "title": meta["title"], "atoms": meta["atoms"],
                                      "chains": meta["chains"], "lod": self.default_lod(meta)},
                  key=f"molecule:{meta['id']}", ttl=1800)


library = Library()
