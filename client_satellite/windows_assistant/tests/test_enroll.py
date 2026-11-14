import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from connection import enroll
from connection.client import Client, ServerError
from settings import store

PIN = "ab" * 32
TOKEN = "T" * 43


def payload(**changes) -> dict:
    return {"server": "https://192.168.1.10:8443", "token": TOKEN, "pin": PIN, "expires": int(time.time()) + 600, **changes}


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / "enroll.json"

    def write(self, data) -> None:
        self.path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")

    def test_missing_file_means_manual_pairing(self):
        self.assertIsNone(enroll.load(self.path))

    def test_valid_file_is_returned(self):
        self.write(payload())
        self.assertEqual(enroll.load(self.path)["token"], TOKEN)

    def test_invalid_files_are_rejected_with_a_translation_key(self):
        cases = {"enroll.file_invalid": [payload(server="http://192.168.1.10"), payload(pin="zz"), payload(token="corto"),
                                         payload(expires="domani"), "non json", "[1]", payload(token=None)],
                 "enroll.file_expired": [payload(expires=int(time.time()) - 5)]}
        for key, items in cases.items():
            for item in items:
                self.write(item)
                with self.assertRaises(enroll.EnrollError) as ctx:
                    enroll.load(self.path)
                self.assertEqual(ctx.exception.key, key)

    def test_oversized_file_is_rejected(self):
        self.write(json.dumps(payload(pad="x" * enroll.FILE_LIMIT)))
        with self.assertRaises(enroll.EnrollError):
            enroll.load(self.path)

    def test_wipe_removes_the_file(self):
        self.write(payload())
        enroll.wipe(self.path)
        self.assertFalse(self.path.exists())


class RedeemTest(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(store.DEFAULTS, name="Ufficio PC")
        saved = mock.patch.object(store, "save")
        self.saved = saved.start()
        self.addCleanup(saved.stop)

    def contact(self, fingerprint=PIN):
        return lambda server: (fingerprint, "PEM")

    def test_matching_pin_enrolls_and_stores_the_credentials(self):
        with mock.patch.object(Client, "enroll", return_value="node-token") as call:
            enroll.redeem(self.cfg, payload(), self.contact())
        self.assertRegex(self.cfg["node_id"], r"^pc-ufficio-pc-[0-9a-f]{24}$")
        call.assert_called_once_with(TOKEN, self.cfg["node_id"], "Ufficio PC")
        self.assertEqual((self.cfg["token"], self.cfg["pin"], self.cfg["ca"]), ("node-token", PIN, "PEM"))
        self.saved.assert_called_once()

    def test_equal_display_names_do_not_reuse_node_identity(self):
        self.assertNotEqual(store.node_id_for("Ufficio PC"), store.node_id_for("Ufficio PC"))

    def test_certificate_that_differs_from_the_package_is_refused_before_sending_the_token(self):
        with mock.patch.object(Client, "enroll") as call:
            with self.assertRaises(enroll.EnrollError) as ctx:
                enroll.redeem(self.cfg, payload(), self.contact("cd" * 32))
        self.assertEqual(ctx.exception.key, "enroll.pin_mismatch")
        call.assert_not_called()
        self.assertEqual(self.cfg["token"], "")

    def test_server_codes_become_translation_keys(self):
        for code, key in (("enroll_token_invalid", "enroll.token_invalid"), ("enroll_node_exists", "enroll.node_exists"),
                          ("rate_limited", "enroll.rate_limited"), ("altro", "enroll.unreachable")):
            with mock.patch.object(Client, "enroll", side_effect=ServerError(code)):
                with self.assertRaises(enroll.EnrollError) as ctx:
                    enroll.redeem(self.cfg, payload(), self.contact())
            self.assertEqual(ctx.exception.key, key)

    def test_unreachable_server_is_reported(self):
        def failing(server):
            raise ServerError("giù")

        with self.assertRaises(enroll.EnrollError) as ctx:
            enroll.redeem(self.cfg, payload(), failing)
        self.assertEqual(ctx.exception.key, "enroll.unreachable")


class TrailerTest(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "Nuxiva_Setup.exe"

    def build(self, data: dict, base: bytes = b"MZ" + b"\0" * 5000) -> None:
        raw = json.dumps(data).encode()
        self.path.write_bytes(base + raw + len(raw).to_bytes(4, "big") + enroll.TRAILER_MAGIC)

    def test_a_clean_installer_has_no_enrollment(self):
        self.path.write_bytes(b"MZ" + b"\0" * 5000)
        self.assertIsNone(enroll.load_trailer(self.path))

    def test_a_tiny_file_has_no_enrollment(self):
        self.path.write_bytes(b"MZ")
        self.assertIsNone(enroll.load_trailer(self.path))

    def test_the_appended_block_is_read_and_validated(self):
        self.build(payload())
        self.assertEqual(enroll.load_trailer(self.path)["token"], TOKEN)

    def test_an_expired_or_malformed_block_is_rejected(self):
        for data, key in ((payload(expires=int(time.time()) - 5), "enroll.file_expired"), (payload(token="corto"), "enroll.file_invalid"),
                          (payload(server="http://x"), "enroll.file_invalid")):
            self.build(data)
            with self.assertRaises(enroll.EnrollError) as ctx:
                enroll.load_trailer(self.path)
            self.assertEqual(ctx.exception.key, key)

    def test_an_impossible_length_is_rejected(self):
        self.path.write_bytes(b"MZ" + (60000).to_bytes(4, "big") + enroll.TRAILER_MAGIC)
        with self.assertRaises(enroll.EnrollError):
            enroll.load_trailer(self.path)

    def test_source_arguments_are_recognised(self):
        self.assertEqual(enroll.enrollment_source(["x", "--enrollment-installer", "a.exe"]), ("installer", Path("a.exe")))
        self.assertEqual(enroll.enrollment_source(["x", "--enrollment-file", "e.json"]), ("file", Path("e.json")))
        self.assertIsNone(enroll.enrollment_source(["x"]))


if __name__ == "__main__":
    unittest.main()
