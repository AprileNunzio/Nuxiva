import json
import re
import secrets
import time

from agenti.nodes import trust
from agenti.nodes.enrollment import tokens
from agenti.nodes.registry import registry

BAUD = 115200
MAX_EVENT_BYTES = 65536
HELLO_TIMEOUT = 6.0
PROVISION_TIMEOUT = 10.0
ENROLL_TIMEOUT = 75.0
ENROLL_TTL = 3600
PORT_RE = re.compile(r"^(/dev/(ttyUSB|ttyACM|cu\.[A-Za-z0-9._-]+)[0-9]*|COM[0-9]{1,3})$")
SLUG_RE = re.compile(r"[^a-z0-9]+")


class Esp32Error(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def clean_port(port: str, allowed: set[str]) -> str:
    value = str(port or "").strip()
    if not PORT_RE.fullmatch(value) or value not in allowed:
        raise Esp32Error("esp32.error.port")
    return value


def clean_credentials(ssid: str, password: str, name: str) -> tuple[str, str, str]:
    ssid, password, name = str(ssid or ""), str(password or ""), " ".join(str(name or "").split())
    if not 1 <= len(ssid.encode("utf-8")) <= 32 or any(ord(c) < 32 or ord(c) == 127 for c in ssid):
        raise Esp32Error("esp32.error.ssid")
    if password and (not 8 <= len(password) <= 63 or any(not 32 <= ord(c) <= 126 for c in password)):
        raise Esp32Error("esp32.error.password")
    if not 1 <= len(name) <= 60 or any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise Esp32Error("esp32.error.name")
    return ssid, password, name


def node_id_for(name: str) -> str:
    slug = SLUG_RE.sub("-", name.lower()).strip("-")[:24] or "nodo"
    for _ in range(8):
        candidate = f"esp32-{slug}-{secrets.token_hex(2)}"
        if candidate not in registry.data["nodes"]:
            return candidate
    raise Esp32Error("esp32.error.id")


def build_provision(origin: str, ca_pem: str, pin: str, token: str, node_id: str, ssid: str, password: str, name: str) -> str:
    return json.dumps({"cmd": "provision", "v": 1, "ssid": ssid, "pass": password, "server": origin, "ca": ca_pem,
                       "token": token, "id": node_id, "name": name, "pin": pin}, separators=(",", ":"))


class Channel:
    def __init__(self, link) -> None:
        self.link = link
        self.read = 0

    def send(self, line: str) -> None:
        self.link.write(line.encode("utf-8") + b"\n")
        self.link.flush()

    def wait(self, names: set[str], timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            raw = self.link.readline()
            self.read += len(raw)
            if self.read > MAX_EVENT_BYTES:
                raise Esp32Error("esp32.error.noise")
            if not raw:
                continue
            try:
                event = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get("event")
            if kind == "error":
                raise Esp32Error(f"esp32.device.{re.sub('[^a-z_]', '', str(event.get('code', 'unknown')))[:32] or 'unknown'}")
            status = event.get("status")
            if kind == "enroll" and event.get("ok") is False and "enroll" in names and isinstance(status, int) and status > 0:
                raise Esp32Error(f"esp32.enroll.{status}")
            if kind in names:
                return event
        raise Esp32Error("esp32.error.timeout")


def provision(link, host: str, https_port: int, ssid: str, password: str, name: str) -> dict:
    ssid, password, name = clean_credentials(ssid, password, name)
    origin = trust.https_origin(host, https_port)
    if not origin:
        raise Esp32Error("esp32.error.https_unavailable")
    pin = trust.ca_pin()
    if not pin:
        raise Esp32Error("esp32.error.ca_missing")
    ca_pem = trust.CA_FILE.read_text(encoding="ascii")
    channel = Channel(link)
    channel.send('{"cmd":"hello"}')
    info = channel.wait({"info", "ready"}, HELLO_TIMEOUT)
    if info.get("enrolled") is True:
        raise Esp32Error("esp32.error.already_enrolled")
    public = str(info.get("pub", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", public):
        raise Esp32Error("esp32.error.identity")
    node_id = node_id_for(name)
    token, _ = tokens.issue(ENROLL_TTL)
    channel.send(build_provision(origin, ca_pem, pin, token, node_id, ssid, password, name))
    provisioned = channel.wait({"provisioned"}, PROVISION_TIMEOUT)
    if str(provisioned.get("pub", "")) != public:
        raise Esp32Error("esp32.error.identity")
    channel.wait({"enroll"}, ENROLL_TIMEOUT)
    node = registry.data["nodes"].get(node_id)
    if node is None or node.get("pubkey") != public:
        raise Esp32Error("esp32.error.identity")
    return {"node_id": node_id, "name": name, "fingerprint": str(provisioned.get("fingerprint", "")),
            "pairing_code": str(provisioned.get("pairing_code", "")), "firmware": str(provisioned.get("fw", "")),
            "flash_encrypted": bool(provisioned.get("flash_encrypted"))}


def open_port(port: str):
    import serial

    return serial.Serial(port, BAUD, timeout=0.5, write_timeout=3)
