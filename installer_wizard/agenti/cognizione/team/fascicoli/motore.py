import json
import os

from agenti.team.fascicoli import formato, oscura
from agenti.team.fascicoli.archivio import PyStore, StoreError


def _native():
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    return nuxiva_native if hasattr(nuxiva_native, "RustDossierStore") else None


_rust = _native()
ENGINE = "rust" if _rust is not None else "python"


def _problems(exc: Exception) -> list:
    try:
        value = json.loads(str(exc))
    except ValueError:
        return []
    return value if isinstance(value, list) else []


class RustStore:
    def __init__(self, root: str, key: bytes) -> None:
        self._inner = _rust.RustDossierStore(root, key)

    def open(self, level: str, now_ms: int) -> str:
        return self._inner.open(level, now_ms)

    def write(self, rel: str, name: str, doc: dict, now_ms: int) -> str:
        try:
            return self._inner.write(rel, name, json.dumps(doc, ensure_ascii=False), now_ms)
        except ValueError as exc:
            problems = _problems(exc)
            raise StoreError("invalid" if problems else str(exc), problems) from exc

    def read(self, rel: str, name: str) -> dict:
        return json.loads(self._inner.read(rel, name))

    def verify(self, rel: str) -> dict:
        return json.loads(self._inner.verify(rel))

    def expired(self, now_ms: int, days: int, limit: int) -> list[str]:
        return self._inner.expired(now_ms, days, limit)

    def prune(self, rel: str, now_ms: int) -> int:
        return self._inner.prune(rel, now_ms)


def store(root: str, key: bytes, native: bool = True):
    return RustStore(root, key) if native and _rust is not None else PyStore(root, key)


def render(doc: dict) -> str:
    return _rust.dossier_render(json.dumps(doc, ensure_ascii=False)) if _rust else formato.render(doc)


def redact(text: str) -> str:
    return _rust.dossier_redact(text) if _rust else oscura.redact(text)


def step_file(number: int, slug: str) -> str | None:
    return _rust.dossier_step_file(number, slug) if _rust else formato.step_file(number, slug)
