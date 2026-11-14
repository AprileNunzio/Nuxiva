import hmac
import json
import logging
import os
import re
import time
from pathlib import Path

from connection.client import Client, ServerError
from connection.devicekey import DeviceKey
from settings import store

log = logging.getLogger("nuxiva.enroll")
ENROLL_FILE = "enroll.json"
FILE_LIMIT = 4096
TRAILER_MAGIC = b"NXENROL1"
LENGTH_SIZE = 4
TRAILER_TAIL = LENGTH_SIZE + len(TRAILER_MAGIC)
PIN_RE = re.compile(r"[0-9a-f]{64}")
TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{20,128}")
SERVER_ERRORS = {
    "enroll_token_invalid": "enroll.token_invalid",
    "enroll_node_exists": "enroll.node_exists",
    "rate_limited": "enroll.rate_limited",
}


class EnrollError(Exception):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def parse(raw: bytes) -> dict:
    try:
        data = json.loads(raw.decode("utf-8")) if len(raw) <= FILE_LIMIT else None
    except ValueError as exc:
        log.error("Dati di iscrizione illeggibili: %s", exc)
        raise EnrollError("enroll.file_invalid") from exc
    if not isinstance(data, dict):
        raise EnrollError("enroll.file_invalid")
    server, token, pin, expires = (data.get("server"), data.get("token"), data.get("pin"), data.get("expires"))
    if not (isinstance(server, str) and server.startswith("https://") and isinstance(token, str) and TOKEN_RE.fullmatch(token)
            and isinstance(pin, str) and PIN_RE.fullmatch(pin) and isinstance(expires, int) and not isinstance(expires, bool)):
        raise EnrollError("enroll.file_invalid")
    if expires < time.time():
        raise EnrollError("enroll.file_expired")
    return data


def load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()[:FILE_LIMIT + 1]
    except OSError as exc:
        log.error("File di iscrizione illeggibile: %s", exc)
        raise EnrollError("enroll.file_invalid") from exc
    return parse(raw)


def load_trailer(path: Path) -> dict | None:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            if size < TRAILER_TAIL:
                return None
            handle.seek(size - TRAILER_TAIL)
            tail = handle.read(TRAILER_TAIL)
            if tail[LENGTH_SIZE:] != TRAILER_MAGIC:
                return None
            length = int.from_bytes(tail[:LENGTH_SIZE], "big")
            if not 0 < length <= FILE_LIMIT or length > size - TRAILER_TAIL:
                raise EnrollError("enroll.file_invalid")
            handle.seek(size - TRAILER_TAIL - length)
            raw = handle.read(length)
    except OSError as exc:
        log.error("Installer illeggibile: %s", exc)
        raise EnrollError("enroll.file_invalid") from exc
    return parse(raw)


def enrollment_source(argv: list[str]) -> tuple[str, Path] | None:
    if len(argv) == 3 and argv[1] in ("--enrollment-file", "--enrollment-installer"):
        return ("installer" if argv[1] == "--enrollment-installer" else "file", Path(argv[2]))
    return None


def redeem(cfg: dict, data: dict, first_contact, name: str | None = None) -> None:
    try:
        server = store.normalize_server(data["server"])
    except ValueError as exc:
        raise EnrollError("enroll.file_invalid") from exc
    try:
        fingerprint, ca_pem = first_contact(server)
    except ServerError as exc:
        raise EnrollError("enroll.unreachable") from exc
    if not hmac.compare_digest(fingerprint, data["pin"]):
        raise EnrollError("enroll.pin_mismatch")
    name = name or cfg["name"]
    node_id = store.node_id_for(name)
    key = DeviceKey.generate()
    try:
        token = Client(server, node_id, "", ca_pem, key).enroll(data["token"], node_id, name)
    except ServerError as exc:
        raise EnrollError(SERVER_ERRORS.get(str(exc), "enroll.unreachable")) from exc
    cfg.update(server=server, name=name, node_id=node_id, token=token, pin=fingerprint, ca=ca_pem, key=key.seed_hex())
    store.save(cfg)


def wipe(path: Path) -> None:
    try:
        size = path.stat().st_size
        with path.open("r+b") as handle:
            handle.write(b"\0" * size)
            handle.flush()
            os.fsync(handle.fileno())
        path.unlink()
    except OSError as exc:
        log.error("Impossibile eliminare il file di iscrizione %s: %s", path, exc)
