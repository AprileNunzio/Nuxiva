import hashlib
import hmac
import json
import logging
import os
import secrets
import threading

from config import STATE_DIR

from agenti.authz.access import COLUMNS, Matrix, MatrixError, PythonEngine

FOLDER = STATE_DIR / "authz"
MATRIX_FILE = FOLDER / "matrix.json"
SIGNATURE_FILE = FOLDER / "matrix.sig"
KEY_FILE = FOLDER / "matrix.key"
log = logging.getLogger("nuxiva.authz.matrix")


def _native(raw: str | None):
    if os.environ.get("NUXIVA_NATIVE", "auto").strip() == "0":
        return None
    try:
        import nuxiva_native
    except ImportError:
        return None
    engine = getattr(nuxiva_native, "RustAccessMatrix", None)
    if engine is None:
        return None
    try:
        return engine(raw)
    except ValueError as exc:
        raise MatrixError(str(exc)) from exc


def build(raw: str | None):
    return _native(raw) or PythonEngine(raw)


def _write(path, data: bytes, mode: int = 0o600) -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.replace(tmp, path)


def _key(create: bool) -> bytes | None:
    try:
        return KEY_FILE.read_bytes()
    except FileNotFoundError:
        if not create:
            return None
    key = secrets.token_bytes(32)
    _write(KEY_FILE, key)
    return key


def _sign(raw: bytes, key: bytes) -> str:
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


class AccessStore:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._engine = None
        self.source = "builtin"

    def _override(self) -> str | None:
        try:
            raw = MATRIX_FILE.read_bytes()
            signature = SIGNATURE_FILE.read_text(encoding="ascii").strip()
        except FileNotFoundError:
            return None
        key = _key(False)
        if key is None or not hmac.compare_digest(_sign(raw, key), signature):
            log.error("Matrice dei permessi con firma non valida: uso la matrice predefinita")
            return None
        return raw.decode("utf-8")

    def load(self) -> None:
        raw, source = None, "builtin"
        try:
            raw = self._override()
        except (OSError, UnicodeDecodeError) as exc:
            log.error("Matrice dei permessi illeggibile, uso la predefinita: %s", exc)
        engine = build(None)
        if raw is not None:
            try:
                engine, source = build(raw), "custom"
            except MatrixError as exc:
                log.error("Matrice dei permessi non valida (%s), uso la predefinita", exc.code)
        with self._lock:
            self._engine, self.source = engine, source

    @property
    def engine(self):
        if self._engine is None:
            self.load()
        return self._engine

    def decide(self, capabilities: list[str], role: str, level: str, local: bool | None, own: bool) -> tuple[str, str]:
        return self.engine.decide(capabilities, role, level, local, own)

    def export(self) -> dict:
        return {"source": self.source, "roles": list(COLUMNS), "rules": json.loads(self.engine.export())}

    @staticmethod
    def preview(data: dict) -> dict:
        raw = json.dumps(data)
        proposed = json.loads(build(raw).export())
        current = json.loads(store.engine.export())
        changes = []
        for key in sorted(set(proposed) | set(current)):
            for i, role in enumerate(COLUMNS):
                before = (current.get(key) or [None] * len(COLUMNS))[i]
                after = (proposed.get(key) or [None] * len(COLUMNS))[i]
                if before != after:
                    changes.append({"capability": key, "role": role, "before": before, "after": after})
        asked = data.get("rules") if isinstance(data.get("rules"), dict) else {}
        hardened = [{"capability": k, "role": COLUMNS[i], "asked": cells[i], "kept": proposed[k][i]}
                    for k, cells in asked.items() if k in proposed
                    for i in range(len(COLUMNS)) if isinstance(cells, list) and i < len(cells) and cells[i] != proposed[k][i]]
        return {"changes": changes, "hardened": hardened}

    def save(self, data: dict) -> dict:
        raw = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8")
        Matrix.parse(raw.decode("utf-8"))
        build(raw.decode("utf-8"))
        key = _key(True)
        _write(MATRIX_FILE, raw)
        _write(SIGNATURE_FILE, _sign(raw, key).encode("ascii"))
        self.load()
        return self.export()

    def reset(self) -> dict:
        for path in (MATRIX_FILE, SIGNATURE_FILE):
            path.unlink(missing_ok=True)
        self.load()
        return self.export()


store = AccessStore()
