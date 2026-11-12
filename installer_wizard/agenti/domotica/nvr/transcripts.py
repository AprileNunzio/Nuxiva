import json
import logging
import re
import secrets

from config import STATE_DIR
from agenti.nvr import fuse_py, nvm2
from agenti.nvr.vault import MediaVault, _private_write, clean_id, media_vault
import native_module

log = logging.getLogger("nuxiva.nvr.transcripts")
ROOT = STATE_DIR / "nvr" / "transcripts"
MIN_OVERLAP = 0.5
MAX_TURNS = 5000
SLUG = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")


def fuse(rows: list[dict], min_overlap: float = MIN_OVERLAP) -> list[dict]:
    fn = native_module.feature("nvr_fuse")
    if fn is None:
        native_module.python_fallback("nvr.fuse")
        return fuse_py.py_fuse(rows, min_overlap)
    return json.loads(fn(json.dumps(rows), float(min_overlap)))


class TranscriptStore:
    def __init__(self, vault: MediaVault | None = None) -> None:
        self.vault = vault or media_vault
        self.root = ROOT

    def _context(self, camera: str, segment: str) -> str:
        return f"nvr.transcript|{clean_id(camera)}|{clean_id(segment)}"

    def path(self, camera: str, segment: str):
        return self.root / clean_id(camera) / f"{clean_id(segment)}.nvb"

    def _engine(self):
        cls = native_module.feature("RustMediaVault")
        return cls(self.vault._master_key()) if cls is not None and hasattr(cls, "seal_blob") else None

    def save(self, camera: str, segment: str, data: dict) -> None:
        plain = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        nonce = secrets.token_bytes(nvm2.NONCE_LEN)
        engine = self._engine()
        context = self._context(camera, segment)
        blob = bytes(engine.seal_blob(context, nonce, plain)) if engine is not None \
            else nvm2.py_seal_blob(self.vault._master_key(), context, nonce, plain)
        _private_write(self.path(camera, segment), blob)

    def load(self, camera: str, segment: str) -> dict | None:
        path = self.path(camera, segment)
        if not path.exists():
            return None
        blob = path.read_bytes()
        engine = self._engine()
        context = self._context(camera, segment)
        plain = bytes(engine.open_blob(context, blob)) if engine is not None \
            else nvm2.py_open_blob(self.vault._master_key(), context, blob)
        return json.loads(plain.decode("utf-8"))

    def exists(self, camera: str, segment: str) -> bool:
        return self.path(camera, segment).exists()

    def delete(self, camera: str, segment: str) -> bool:
        path = self.path(camera, segment)
        existed = path.exists()
        path.unlink(missing_ok=True)
        return existed

    def turns(self, camera: str, from_ms: int, to_ms: int) -> list[dict]:
        from agenti.nvr.archive import archive
        out = []
        for seg in archive.catalog.range(camera, from_ms, to_ms, 2000):
            if not seg["audio"]:
                continue
            try:
                data = self.load(camera, seg["id"])
            except (OSError, ValueError) as exc:
                log.warning("NVR: trascrizione %s/%s illeggibile: %s", camera, seg["id"], exc)
                continue
            for turn in (data or {}).get("turns", []):
                if from_ms <= turn["start_ms"] < to_ms:
                    out.append({**turn, "camera": camera, "segment": seg["id"]})
        return sorted(out, key=lambda t: t["start_ms"])[:MAX_TURNS]


store = TranscriptStore()


def transcript_markers(camera: str, from_ms: int, to_ms: int) -> list[dict]:
    rows = store.turns(camera, from_ms, to_ms)
    return [{"at_ms": t["start_ms"], "camera": camera, "kind": "speech", "id": f"tx:{t['segment']}:{t['start_ms']}",
             "label": t["text"][:200], "score": float(t.get("speaker_score") or 0.0)} for t in rows]


def room_transcript(cameras: dict[str, float], from_ms: int, to_ms: int) -> list[dict]:
    rows = []
    for camera, weight in cameras.items():
        for t in store.turns(camera, from_ms, to_ms):
            speaker = t.get("speaker") if SLUG.match(str(t.get("speaker") or "")) else None
            rows.append({"source": camera, "start_ms": t["start_ms"], "end_ms": max(t["end_ms"], t["start_ms"] + 1),
                         "text": t["text"], "speaker": speaker,
                         "speaker_score": float(t.get("speaker_score") or 0.0), "weight": float(weight)})
    return fuse(rows)
