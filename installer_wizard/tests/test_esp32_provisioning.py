import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti.nodes import enrollment as enrollment_module
from agenti.nodes import esp32
from agenti.nodes import registry as registry_module

PUBLIC = "ea4a6c63e29c520abef5507b132ec5f9954776aebebe7b92421eea691446d22c"
OTHER = "fd1724385aa0c75b64fb78cd602fa1d991fdebf76b13c58ed702eac835e9f618"


def make_ca() -> tuple[str, str]:
    der = bytes((i * 37 + 11) & 0xFF for i in range(700))
    body = base64.b64encode(der).decode()
    pem = "-----BEGIN CERTIFICATE-----\n" + "\n".join(body[i:i + 64] for i in range(0, len(body), 64)) + "\n-----END CERTIFICATE-----\n"
    return pem, hashlib.sha256(der).hexdigest()


class FakeFirmware:
    def __init__(self, registry, tokens, enrolled=False, error=None, silent=False, fail_enroll=None, wrong_pub=False):
        self.registry, self.tokens = registry, tokens
        self.enrolled, self.error, self.silent = enrolled, error, silent
        self.fail_enroll, self.wrong_pub = fail_enroll, wrong_pub
        self.outbox: list[bytes] = [b"boot: rst:0x1 (POWERON)\n", b"{not json\n"]
        self.received: list[dict] = []

    def write(self, data: bytes) -> None:
        if self.silent:
            return
        command = json.loads(data.decode())
        self.received.append(command)
        if command["cmd"] == "hello":
            self.emit({"event": "info", "fw": "1.0.0", "enrolled": self.enrolled, "pub": PUBLIC})
        elif command["cmd"] == "provision":
            self.provision(command)

    def provision(self, command: dict) -> None:
        if self.error:
            self.emit({"event": "error", "code": self.error})
            return
        pem = command["ca"]
        der = base64.b64decode("".join(pem.splitlines()[1:-1]))
        assert hashlib.sha256(der).hexdigest() == command["pin"]
        self.emit({"event": "provisioned", "fw": "1.0.0", "pub": PUBLIC, "pairing_code": "123456",
                   "fingerprint": "AAAA-BBBB-CCCC", "flash_encrypted": False})
        if self.fail_enroll:
            self.emit({"event": "enroll", "ok": False, "status": self.fail_enroll})
            return
        digest = self.tokens.verify(command["token"])
        code = self.registry.new_code()["code"]
        self.registry.pair(code, command["id"], {"pubkey": OTHER if self.wrong_pub else PUBLIC, "type": "esp32",
                                                 "name": command["name"]})
        self.tokens.burn(digest)
        self.emit({"event": "enroll", "ok": True})

    def emit(self, event: dict) -> None:
        self.outbox.append(json.dumps(event).encode() + b"\n")

    def readline(self) -> bytes:
        return self.outbox.pop(0) if self.outbox else b""

    def flush(self) -> None:
        return None


class ProvisioningTest(unittest.TestCase):
    def setUp(self):
        directory = Path(tempfile.mkdtemp())
        self.pem, self.pin = make_ca()
        ca_file = directory / "ca.pem"
        ca_file.write_text(self.pem, encoding="ascii")
        patches = [mock.patch.object(enrollment_module, "TOKENS_FILE", directory / "tokens.json"),
                   mock.patch.object(registry_module, "NODES_FILE", directory / "nodes.json"),
                   mock.patch.object(esp32.trust, "CA_FILE", ca_file),
                   mock.patch.object(esp32, "HELLO_TIMEOUT", 0.05), mock.patch.object(esp32, "PROVISION_TIMEOUT", 0.05),
                   mock.patch.object(esp32, "ENROLL_TIMEOUT", 0.05)]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.registry = registry_module.Registry()
        self.tokens = enrollment_module.EnrollmentTokens()
        for name, value in (("registry", self.registry), ("tokens", self.tokens)):
            patcher = mock.patch.object(esp32, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_flow(self, link, ssid="Casa", password="correct horse", name="Cucina"):
        return esp32.provision(link, "nuxiva.local", 8443, ssid, password, name)

    def test_full_flow_enrolls_the_node_bound_to_the_device_key(self):
        link = FakeFirmware(self.registry, self.tokens)
        result = self.run_flow(link)
        node = self.registry.data["nodes"][result["node_id"]]
        self.assertEqual(node["pubkey"], PUBLIC)
        self.assertEqual(node["type"], "esp32")
        self.assertEqual(result["pairing_code"], "123456")
        self.assertRegex(result["node_id"], r"^esp32-cucina-[0-9a-f]{4}$")
        sent = link.received[1]
        self.assertEqual(sent["server"], "https://nuxiva.local:8443")
        self.assertEqual(sent["pin"], self.pin)
        self.assertEqual(self.tokens.active(), 0)

    def test_enrollment_token_is_single_use_and_short_lived(self):
        link = FakeFirmware(self.registry, self.tokens)
        with mock.patch.object(self.tokens, "issue", wraps=self.tokens.issue) as issue:
            self.run_flow(link)
        issue.assert_called_once_with(esp32.ENROLL_TTL)
        self.assertLessEqual(esp32.ENROLL_TTL, 3600)

    def test_device_already_enrolled_is_refused_without_issuing_a_token(self):
        with self.assertRaises(esp32.Esp32Error) as ctx:
            self.run_flow(FakeFirmware(self.registry, self.tokens, enrolled=True))
        self.assertEqual(ctx.exception.code, "esp32.error.already_enrolled")
        self.assertEqual(self.tokens.active(), 0)

    def test_device_errors_are_reported_with_a_code(self):
        with self.assertRaises(esp32.Esp32Error) as ctx:
            self.run_flow(FakeFirmware(self.registry, self.tokens, error="ca_pin"))
        self.assertEqual(ctx.exception.code, "esp32.device.ca_pin")

    def test_silent_board_times_out(self):
        with self.assertRaises(esp32.Esp32Error) as ctx:
            self.run_flow(FakeFirmware(self.registry, self.tokens, silent=True))
        self.assertEqual(ctx.exception.code, "esp32.error.timeout")

    def test_server_rejection_during_enrollment_is_surfaced(self):
        with self.assertRaises(esp32.Esp32Error) as ctx:
            self.run_flow(FakeFirmware(self.registry, self.tokens, fail_enroll=403))
        self.assertEqual(ctx.exception.code, "esp32.enroll.403")

    def test_registry_key_that_differs_from_the_device_key_is_rejected(self):
        with self.assertRaises(esp32.Esp32Error) as ctx:
            self.run_flow(FakeFirmware(self.registry, self.tokens, wrong_pub=True))
        self.assertEqual(ctx.exception.code, "esp32.error.identity")

    def test_missing_https_or_ca_blocks_before_touching_the_board(self):
        link = FakeFirmware(self.registry, self.tokens)
        with self.assertRaises(esp32.Esp32Error) as ctx:
            esp32.provision(link, "127.0.0.1", 8443, "Casa", "", "Cucina")
        self.assertEqual(ctx.exception.code, "esp32.error.https_unavailable")
        with mock.patch.object(esp32.trust, "ca_pin", return_value=""):
            with self.assertRaises(esp32.Esp32Error) as ctx:
                self.run_flow(link)
        self.assertEqual(ctx.exception.code, "esp32.error.ca_missing")
        self.assertEqual(link.received, [])

    def test_endless_garbage_from_the_board_is_cut_off(self):
        class Noisy:
            def write(self, data):
                return None

            def flush(self):
                return None

            def readline(self):
                return b"x" * 4096 + b"\n"

        with mock.patch.object(esp32, "HELLO_TIMEOUT", 5.0):
            with self.assertRaises(esp32.Esp32Error) as ctx:
                self.run_flow(Noisy())
        self.assertEqual(ctx.exception.code, "esp32.error.noise")


class InputTest(unittest.TestCase):
    def test_port_must_be_a_detected_serial_device(self):
        allowed = {"/dev/ttyUSB0", "COM3"}
        self.assertEqual(esp32.clean_port("/dev/ttyUSB0", allowed), "/dev/ttyUSB0")
        self.assertEqual(esp32.clean_port("COM3", allowed), "COM3")
        for bad in ("/dev/ttyUSB1", "/etc/passwd", "../dev/ttyUSB0", "", None, "/dev/ttyUSB0;rm", "/dev/sda"):
            with self.assertRaises(esp32.Esp32Error):
                esp32.clean_port(bad, allowed)

    def test_credentials_follow_wifi_and_device_limits(self):
        self.assertEqual(esp32.clean_credentials("Casa", "", " Cucina  nord ")[2], "Cucina nord")
        for ssid, password, name in (("", "x" * 8, "a"), ("a" * 33, "", "a"), ("Casa", "short", "a"), ("Casa", "p" * 64, "a"),
                                     ("Casa", "pass\nword", "a"), ("Casa", "", ""), ("Casa", "", "n" * 61), ("a\x00", "", "a")):
            with self.assertRaises(esp32.Esp32Error):
                esp32.clean_credentials(ssid, password, name)

    def test_provision_line_is_compact_json_the_firmware_can_parse(self):
        line = esp32.build_provision("https://h:1", "PEM", "p" * 64, "t" * 32, "esp32-a-0000", "S", "", "N")
        self.assertNotIn("\n", line)
        self.assertEqual(json.loads(line)["cmd"], "provision")
        self.assertEqual(json.loads(line)["v"], 1)


if __name__ == "__main__":
    unittest.main()
