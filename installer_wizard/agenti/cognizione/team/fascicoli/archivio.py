import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import time
from pathlib import Path

from agenti.team.fascicoli import formato
from agenti.team.fascicoli.oscura import redact

LEDGER = "registro.jsonl"
KEEP_AFTER_PRUNE = "99-esito.md"
DOMAIN = b"nuxiva-agency-ledger-v1"
MAX_LINE = 512 * 1024
_ID = re.compile(r"[0-9]{8}-[0-9]{6}-[0-9a-f]{6}")
_REL = re.compile(r"[0-9]{4}/[0-9]{2}/[0-9]{2}/[0-9]{8}-[0-9]{6}-[0-9a-f]{6}")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class StoreError(Exception):
    def __init__(self, code: str, problems: list | None = None) -> None:
        super().__init__(code)
        self.code, self.problems = code, problems or []


def stamp(ms: int) -> time.struct_time:
    return time.gmtime(ms // 1000)


def iso(ms: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", stamp(ms))


def operation_id(ms: int, suffix: bytes) -> str:
    return time.strftime("%Y%m%d-%H%M%S", stamp(ms)) + "-" + suffix.hex()


def day_path(ms: int) -> str:
    return time.strftime("%Y/%m/%d", stamp(ms))


def _payload(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _mac(key: bytes, seq: int, at_ms: int, kind: str, payload: bytes, prev: bytes) -> bytes:
    kb = kind.encode()
    msg = (DOMAIN + seq.to_bytes(8, "big") + at_ms.to_bytes(8, "big") + len(kb).to_bytes(8, "big") + kb
           + len(payload).to_bytes(8, "big") + payload + prev)
    return hmac.new(key, msg, hashlib.sha256).digest()


def _valid_kind(kind: str) -> bool:
    return 0 < len(kind) <= 64 and all(c.isascii() and (c.islower() or c.isdigit() or c in "._-") for c in kind)


class Ledger:
    def __init__(self, path: Path, key: bytes) -> None:
        self.path, self.key = path, key
        self.head, self.seq, self.entries = bytes(32), 0, []
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | _NOFOLLOW, 0o600)
        with os.fdopen(fd, "rb") as handle:
            for number, raw in enumerate(handle, 1):
                if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
                    raise StoreError("ledger_malformed")
                try:
                    self._accept(json.loads(raw))
                except (ValueError, KeyError, TypeError) as exc:
                    raise StoreError("ledger_malformed") from exc

    def _accept(self, entry: dict) -> None:
        if set(entry) != {"seq", "at_ms", "kind", "payload", "prev", "mac"} or entry["seq"] != self.seq:
            raise StoreError("ledger_sequence")
        if not _valid_kind(entry["kind"]) or bytes.fromhex(entry["prev"]) != self.head:
            raise StoreError("ledger_link")
        tag = bytes.fromhex(entry["mac"])
        want = _mac(self.key, entry["seq"], entry["at_ms"], entry["kind"], _payload(entry["payload"]), self.head)
        if len(tag) != 32 or not hmac.compare_digest(tag, want):
            raise StoreError("ledger_signature")
        self.head, self.seq = tag, self.seq + 1
        self.entries.append(entry)

    def append(self, kind: str, payload: dict, at_ms: int) -> None:
        if not _valid_kind(kind):
            raise StoreError("ledger_kind")
        tag = _mac(self.key, self.seq, at_ms, kind, _payload(payload), self.head)
        entry = {"seq": self.seq, "at_ms": at_ms, "kind": kind, "payload": payload, "prev": self.head.hex(), "mac": tag.hex()}
        line = (json.dumps(entry, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | _NOFOLLOW)
        try:
            os.write(fd, line)
            os.fsync(fd)
        finally:
            os.close(fd)
        self.head, self.seq = tag, self.seq + 1
        self.entries.append(entry)


def _private_dir(path: Path) -> None:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        os.mkdir(path, 0o700)
        return
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise StoreError("not_a_directory")


def _read(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | _NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        data = handle.read(formato.MAX_DOC + 1)
    if len(data) > formato.MAX_DOC:
        raise StoreError("file_too_large")
    return data


def _atomic(folder: Path, name: str, data: bytes) -> None:
    tmp = folder / f".{name}.{secrets.token_hex(8)}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, folder / name)
        dfd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        tmp.unlink(missing_ok=True)


class PyStore:
    def __init__(self, root: str, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("key must be 32 bytes")
        info = os.lstat(root)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("root_not_directory")
        self.root, self.key = Path(root), bytes(key)

    def _dir(self, rel: str) -> Path:
        if not _REL.fullmatch(rel):
            raise StoreError("bad_operation")
        return self.root / rel

    def open(self, level: str, now_ms: int) -> str:
        if level not in formato.LEVELS:
            raise ValueError("unknown level")
        op = operation_id(now_ms, secrets.token_bytes(3))
        rel = f"{day_path(now_ms)}/{op}"
        path = self.root
        for part in rel.split("/"):
            path = path / part
            _private_dir(path)
        ledger = Ledger(path / LEDGER, self.key)
        if ledger.seq:
            raise StoreError("operation_exists")
        ledger.append("dossier.open", {"id": op, "level": level}, now_ms)
        return rel

    def write(self, rel: str, name: str, doc: dict, now_ms: int) -> str:
        kind = formato.kind_of_name(name)
        if kind is None:
            raise StoreError("bad_file_name")
        clean = formato.sanitize(doc)
        problems = formato.validate(clean, kind)
        if problems:
            raise StoreError("invalid", problems)
        base = self._dir(rel)
        _private_dir(base)
        folder, file = base, name
        if "/" in name:
            sub, file = name.split("/", 1)
            folder = base / sub
            _private_dir(folder)
        text = redact(formato.render(clean)).encode()
        if len(text) > formato.MAX_DOC:
            raise StoreError("invalid", [{"at": "", "code": "too_large"}])
        sha = hashlib.sha256(text).hexdigest()
        ledger = Ledger(base / LEDGER, self.key)
        if not ledger.seq:
            raise StoreError("operation_not_open")
        _atomic(folder, file, text)
        ledger.append("dossier.write", {"file": name, "sha256": sha, "bytes": len(text)}, now_ms)
        return sha

    def read(self, rel: str, name: str) -> dict:
        if formato.kind_of_name(name) is None:
            raise StoreError("bad_file_name")
        return formato.parse(_read(self._dir(rel) / name).decode("utf-8"))

    @staticmethod
    def _on_disk(folder: Path) -> list[str]:
        out = []
        for entry in os.scandir(folder):
            if entry.is_dir(follow_symlinks=False) and entry.name == "passi":
                out += [f"passi/{s.name}" for s in os.scandir(entry.path)]
            elif entry.name != LEDGER:
                out.append(entry.name)
        return sorted(out)

    def verify(self, rel: str) -> dict:
        folder = self._dir(rel)
        try:
            ledger = Ledger(folder / LEDGER, self.key)
        except (StoreError, OSError, ValueError):
            return {"ok": False, "level": "", "complete": False, "files": [], "problems": [{"at": LEDGER, "code": "chain_broken"}]}
        expected: dict[str, str | None] = {}
        level, problems = "", []
        for entry in ledger.entries:
            payload = entry["payload"]
            if entry["kind"] == "dossier.open":
                level = payload.get("level", "") if isinstance(payload.get("level"), str) else ""
            elif entry["kind"] == "dossier.write":
                if isinstance(payload.get("file"), str):
                    expected[payload["file"]] = payload.get("sha256") if isinstance(payload.get("sha256"), str) else None
            elif entry["kind"] == "dossier.prune":
                for name in payload.get("files", []):
                    if isinstance(name, str):
                        expected[name] = None
            else:
                problems.append({"at": LEDGER, "code": "unknown_entry"})
        files = []
        for name in sorted(expected):
            want = expected[name]
            try:
                data = _read(folder / name)
            except (OSError, StoreError):
                data = None
            if want is not None and data is not None:
                if hashlib.sha256(data).hexdigest() == want:
                    files.append(name)
                else:
                    problems.append({"at": name, "code": "edited"})
            elif want is not None:
                problems.append({"at": name, "code": "missing"})
            elif data is not None:
                problems.append({"at": name, "code": "should_be_pruned"})
        for name in self._on_disk(folder):
            if name not in expected:
                problems.append({"at": name, "code": "unlogged"})
        known = level in formato.LEVELS
        complete = known and all(any(formato.kind_of_name(f) == k for f in files) for k in formato.LEVELS[level])
        return {"ok": not problems and known, "level": level, "complete": complete, "files": files, "problems": problems}

    def recent(self, limit: int) -> list[str]:
        def dirs(base: Path, size: int) -> list[str]:
            return sorted((e.name for e in os.scandir(base)
                           if e.is_dir(follow_symlinks=False) and len(e.name) == size and e.name.isascii() and e.name.isdigit()),
                          reverse=True)

        out: list[str] = []
        limit = min(limit, 1000)
        for y in dirs(self.root, 4):
            for m in dirs(self.root / y, 2):
                for d in dirs(self.root / y / m, 2):
                    day = self.root / y / m / d
                    ids = sorted((e.name for e in os.scandir(day) if e.is_dir(follow_symlinks=False) and _ID.fullmatch(e.name)), reverse=True)
                    for op in ids:
                        out.append(f"{y}/{m}/{d}/{op}")
                        if len(out) >= limit:
                            return out
        return out

    def expired(self, now_ms: int, days: int, limit: int) -> list[str]:
        cutoff = day_path(max(0, now_ms - days * 86_400_000))
        out: list[str] = []

        def dirs(rel: str, size: int) -> list[str]:
            base = self.root / rel if rel else self.root
            return sorted(e.name for e in os.scandir(base)
                          if e.is_dir(follow_symlinks=False) and len(e.name) == size and e.name.isascii() and e.name.isdigit())

        for y in dirs("", 4):
            for m in dirs(y, 2):
                for d in dirs(f"{y}/{m}", 2):
                    day = f"{y}/{m}/{d}"
                    if day >= cutoff:
                        return out
                    ids = sorted(e.name for e in os.scandir(self.root / day) if e.is_dir(follow_symlinks=False) and _ID.fullmatch(e.name))
                    for op in ids:
                        rel = f"{day}/{op}"
                        if any(n != KEEP_AFTER_PRUNE for n in self._on_disk(self.root / rel)):
                            out.append(rel)
                        if len(out) >= limit:
                            return out
        return out

    def prune(self, rel: str, now_ms: int) -> int:
        folder = self._dir(rel)
        ledger = Ledger(folder / LEDGER, self.key)
        doomed = [n for n in self._on_disk(folder) if n != KEEP_AFTER_PRUNE and formato.kind_of_name(n) is not None]
        if not doomed:
            return 0
        ledger.append("dossier.prune", {"files": doomed}, now_ms)
        for name in doomed:
            os.unlink(folder / name)
        steps = folder / "passi"
        if steps.is_dir() and not steps.is_symlink():
            try:
                os.rmdir(steps)
            except OSError:
                pass
        return len(doomed)
