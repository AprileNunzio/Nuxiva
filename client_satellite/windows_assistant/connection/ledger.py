import hashlib
import json
import os
import re
from collections import deque
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from connection import peer_envelope

DOMAIN = "nuxiva-ledger-v1"
GENESIS = "0" * 64
MAX_BLOCKS = 64
SKEW_MS = 60_000
MAX_AUTHORS = 256
MAX_SYNC = 64
MAX_WIRE = 64 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_TRUSTED = 256
VERSION = 1
HASH_RE = re.compile(r"[0-9a-f]{64}")
SIG_RE = re.compile(r"[0-9a-f]{128}")
BLOCK_FIELDS = {"author", "index", "prev", "ts", "addrs", "sig"}
HEAD_FIELDS = {"author", "index", "hash"}
WEAK = {
    bytes.fromhex(item)
    for item in (
        "0100000000000000000000000000000000000000000000000000000000000000",
        "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
        "0000000000000000000000000000000000000000000000000000000000000000",
        "0000000000000000000000000000000000000000000000000000000000000080",
        "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a",
        "c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac03fa",
        "26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05",
        "26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc85",
    )
}


BACKOFF_BASE_MS = 1_000
BACKOFF_CAP_MS = 60_000


def reconnect_delay_ms(attempt: int, jitter: int) -> int:
    base = min(BACKOFF_BASE_MS * (1 << min(max(attempt, 0), 16)), BACKOFF_CAP_MS)
    return base + jitter % max(base // 4, 1)


class LedgerError(ValueError):
    def __init__(self, name: str) -> None:
        super().__init__(f"ledger.error.{name}")
        self.code = f"ledger.error.{name}"


def _int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_id(value) -> None:
    if not isinstance(value, str) or not HASH_RE.fullmatch(value):
        raise LedgerError("field")
    raw = bytes.fromhex(value)
    if raw in WEAK:
        raise LedgerError("field")
    try:
        Ed25519PublicKey.from_public_bytes(raw)
    except ValueError as exc:
        raise LedgerError("field") from exc


def check_addrs(addrs) -> None:
    try:
        peer_envelope.check_addrs(addrs)
    except ValueError as exc:
        raise LedgerError("limit" if str(exc).endswith("limit") else "field") from exc


def addrs_digest(addrs: list[str]) -> str:
    hasher = hashlib.sha256()
    hasher.update(len(addrs).to_bytes(8, "big"))
    for addr in addrs:
        raw = addr.encode("utf-8")
        hasher.update(len(raw).to_bytes(8, "big"))
        hasher.update(raw)
    return hasher.hexdigest()


def signed_bytes(author: str, index: int, prev: str, ts: int, addrs: list[str]) -> bytes:
    return f"{DOMAIN}\n{author}\n{index}\n{prev}\n{ts}\n{addrs_digest(addrs)}".encode("utf-8")


def block_hash(block: dict) -> str:
    hasher = hashlib.sha256()
    hasher.update(signed_bytes(block["author"], block["index"], block["prev"], block["ts"], block["addrs"]))
    hasher.update(block["sig"].encode("ascii"))
    return hasher.hexdigest()


def check_shape(block) -> None:
    if not isinstance(block, dict) or set(block) != BLOCK_FIELDS:
        raise LedgerError("field")
    check_id(block["author"])
    index, ts = block["index"], block["ts"]
    if not _int(index) or not _int(ts) or index < 0 or ts < 0 or index >= 1 << 64 or ts >= 1 << 63:
        raise LedgerError("field")
    prev, sig = block["prev"], block["sig"]
    if not isinstance(prev, str) or not HASH_RE.fullmatch(prev) or not isinstance(sig, str) or not SIG_RE.fullmatch(sig):
        raise LedgerError("field")
    addrs = block["addrs"]
    if not isinstance(addrs, list) or not all(isinstance(a, str) for a in addrs):
        raise LedgerError("field")
    check_addrs(addrs)


def verify(block: dict) -> None:
    check_shape(block)
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(block["author"])).verify(
            bytes.fromhex(block["sig"]),
            signed_bytes(block["author"], block["index"], block["prev"], block["ts"], block["addrs"]),
        )
    except (InvalidSignature, ValueError) as exc:
        raise LedgerError("signature") from exc


class Chain:
    def __init__(self) -> None:
        self.blocks: deque[dict] = deque()

    @property
    def head(self) -> dict | None:
        return self.blocks[-1] if self.blocks else None

    def after(self, index: int | None) -> list[dict]:
        return [b for b in self.blocks if index is None or b["index"] > index]

    def accept(self, block: dict, now: int) -> bool:
        if block["ts"] > now + SKEW_MS:
            raise LedgerError("clock")
        head = self.head
        if head is None:
            self.blocks.append(block)
            return True
        if block["index"] <= head["index"]:
            return self._settle_old(block)
        if block["index"] != head["index"] + 1:
            raise LedgerError("gap")
        if block["prev"] != block_hash(head):
            raise LedgerError("link")
        if block["ts"] < head["ts"]:
            raise LedgerError("clock")
        self.blocks.append(block)
        while len(self.blocks) > MAX_BLOCKS:
            self.blocks.popleft()
        return True

    def _settle_old(self, block: dict) -> bool:
        for known in self.blocks:
            if known["index"] == block["index"]:
                if block_hash(known) == block_hash(block):
                    return False
                raise LedgerError("fork")
        return False


class Ledger:
    def __init__(self, trusted=()) -> None:
        self.trusted: set[str] = set()
        self.chains: dict[str, Chain] = {}
        self.failures: dict[tuple[str, str], int] = {}
        for node in trusted:
            self.enroll(node)

    def enroll(self, node: str) -> None:
        check_id(node)
        if node not in self.trusted and len(self.trusted) >= MAX_TRUSTED:
            raise LedgerError("capacity")
        self.trusted.add(node)

    def revoke(self, node: str) -> bool:
        self.chains.pop(node, None)
        self.failures = {k: v for k, v in self.failures.items() if k[0] != node}
        was = node in self.trusted
        self.trusted.discard(node)
        return was

    def accept(self, block, now: int) -> bool:
        check_shape(block)
        author = block["author"]
        if author not in self.trusted:
            raise LedgerError("untrusted")
        if author not in self.chains and len(self.chains) >= MAX_AUTHORS:
            raise LedgerError("capacity")
        verify(block)
        chain = self.chains.setdefault(author, Chain())
        try:
            applied = chain.accept(block, now)
        finally:
            if chain.head is None:
                self.chains.pop(author, None)
        if applied:
            self.failures = {k: v for k, v in self.failures.items() if k[0] != author}
        return applied

    def latest(self, node: str) -> dict | None:
        chain = self.chains.get(node)
        return chain.head if chain else None

    def candidates(self, node: str) -> list[str]:
        head = self.latest(node)
        if head is None:
            return []
        ranked = sorted((self.failures.get((node, addr), 0), position, addr) for position, addr in enumerate(head["addrs"]))
        return [addr for _, _, addr in ranked]

    def report_failure(self, node: str, addr: str) -> None:
        key = (node, addr)
        self.failures[key] = self.failures.get(key, 0) + 1

    def report_success(self, node: str, addr: str) -> None:
        self.failures.pop((node, addr), None)

    def digest(self) -> list[dict]:
        return [
            {"author": author, "index": chain.head["index"], "hash": block_hash(chain.head)}
            for author, chain in sorted(self.chains.items())
            if chain.head is not None
        ]

    def missing_for(self, remote: list[dict]) -> list[dict]:
        known = {head["author"]: head["index"] for head in remote}
        found: list[dict] = []
        for author, chain in sorted(self.chains.items()):
            found.extend(chain.after(known.get(author)))
            if len(found) >= MAX_SYNC:
                break
        return found[:MAX_SYNC]

    def merge(self, blocks: list[dict], now: int) -> dict:
        report = {"applied": 0, "known": 0, "rejected": 0}
        ordered = sorted(
            blocks[:MAX_SYNC],
            key=lambda b: (b.get("author", "") if isinstance(b, dict) else "", b.get("index", 0) if isinstance(b, dict) and _int(b.get("index")) else 0),
        )
        for block in ordered:
            try:
                report["applied" if self.accept(block, now) else "known"] += 1
            except LedgerError:
                report["rejected"] += 1
        return report

    def answer(self, wire: dict) -> dict | None:
        if wire["t"] == "want":
            head = self.latest(wire["id"])
            return {"t": "have", "block": head} if head else None
        if wire["t"] == "digest":
            blocks = self.missing_for(wire["heads"])
            return {"t": "delta", "blocks": blocks} if blocks else None
        return None

    def absorb(self, wire: dict, now: int) -> dict:
        if wire["t"] == "have":
            return self.merge([wire["block"]], now)
        if wire["t"] == "delta":
            return self.merge(wire["blocks"], now)
        return {"applied": 0, "known": 0, "rejected": 0}

    def digest_request(self) -> dict:
        return {"t": "digest", "heads": self.digest()}


def decode(raw: bytes) -> dict:
    if len(raw) > MAX_WIRE:
        raise LedgerError("limit")
    try:
        wire = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise LedgerError("field") from exc
    if not isinstance(wire, dict):
        raise LedgerError("field")
    kind = wire.get("t")
    if kind == "want" and set(wire) == {"t", "id"}:
        check_id(wire["id"])
    elif kind == "have" and set(wire) == {"t", "block"}:
        check_shape(wire["block"])
    elif kind == "digest" and set(wire) == {"t", "heads"}:
        _check_heads(wire["heads"])
    elif kind == "delta" and set(wire) == {"t", "blocks"}:
        blocks = wire["blocks"]
        if not isinstance(blocks, list):
            raise LedgerError("field")
        if len(blocks) > MAX_SYNC:
            raise LedgerError("limit")
        for block in blocks:
            check_shape(block)
    else:
        raise LedgerError("field")
    return wire


def _check_heads(heads) -> None:
    if not isinstance(heads, list):
        raise LedgerError("field")
    if len(heads) > MAX_AUTHORS:
        raise LedgerError("limit")
    for head in heads:
        if not isinstance(head, dict) or set(head) != HEAD_FIELDS:
            raise LedgerError("field")
        check_id(head["author"])
        if not _int(head["index"]) or head["index"] < 0 or not isinstance(head["hash"], str) or not HASH_RE.fullmatch(head["hash"]):
            raise LedgerError("field")


def encode(wire: dict) -> bytes:
    raw = json.dumps(wire, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if len(raw) > MAX_WIRE:
        raise LedgerError("limit")
    return raw


def dump(ledger: Ledger) -> bytes:
    blocks = [block for _, chain in sorted(ledger.chains.items()) for block in chain.blocks]
    raw = json.dumps({"v": VERSION, "blocks": blocks}, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if len(raw) > MAX_FILE:
        raise LedgerError("limit")
    return raw


def restore(trusted, raw: bytes, now: int) -> Ledger:
    if len(raw) > MAX_FILE:
        raise LedgerError("limit")
    try:
        snapshot = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise LedgerError("corrupt") from exc
    if not isinstance(snapshot, dict) or set(snapshot) != {"v", "blocks"} or snapshot["v"] != VERSION or not isinstance(snapshot["blocks"], list):
        raise LedgerError("corrupt")
    ledger = Ledger(trusted)
    blocks = snapshot["blocks"]
    try:
        for block in sorted(blocks, key=lambda b: (b["author"], b["index"])):
            ledger.accept(block, now)
    except (LedgerError, KeyError, TypeError) as exc:
        raise LedgerError("corrupt") from exc
    return ledger


def save(ledger: Ledger, path: Path) -> None:
    raw = dump(ledger)
    temp = Path(path).with_suffix(".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def load(trusted, path: Path, now: int) -> Ledger:
    try:
        if os.path.getsize(path) > MAX_FILE:
            raise LedgerError("limit")
        raw = Path(path).read_bytes()
    except FileNotFoundError:
        return Ledger(trusted)
    except OSError as exc:
        raise LedgerError("storage") from exc
    return restore(trusted, raw, now)
