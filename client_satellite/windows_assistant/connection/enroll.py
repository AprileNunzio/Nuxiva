import hmac
import json
import logging
import os
import re
import time
from pathlib import Path

from connection.client import Client, ServerError
from settings import store

log = logging.getLogger("nuxiva.enroll")
ENROLL_FILE = "enroll.json"
FILE_LIMIT = 4096
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


def load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()[:FILE_LIMIT + 1]
        data = json.loads(raw.decode("utf-8")) if len(raw) <= FILE_LIMIT else None
    except (OSError, ValueError) as exc:
        log.error("File di iscrizione illeggibile: %s", exc)
        raise EnrollError("enroll.file_invalid") from exc
    if not isinstance(data, dict):
        raise EnrollError("enroll.file_invalid")
    server, token, pin, expires = (data.get("server"), data.get("token"), data.get("pin"), data.get("expires"))
    if not (isinstance(server, str) and server.startswith("https://") and isinstance(token, str) and TOKEN_RE.fullmatch(token)
            and isinstance(pin, str) and PIN_RE.fullmatch(pin) and isinstance(expires, int)):
        raise EnrollError("enroll.file_invalid")
    if expires < time.time():
        raise EnrollError("enroll.file_expired")
    return data


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
    try:
        token = Client(server, node_id, "", ca_pem).enroll(data["token"], node_id, name)
    except ServerError as exc:
        raise EnrollError(SERVER_ERRORS.get(str(exc), "enroll.unreachable")) from exc
    cfg.update(server=server, name=name, node_id=node_id, token=token, pin=fingerprint, ca=ca_pem)
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
