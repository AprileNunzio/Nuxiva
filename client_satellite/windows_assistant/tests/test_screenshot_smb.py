import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from intents import screenshot as shot
from screenshot import clipboard, hotkey, sink, smbauth
from screenshot.credentials import CredentialError, Vault
from screenshot.service import Service

AUTH = {"target": "smb://nas/condivisa", "user": "nuxiva-share", "password": "Batteria-Corretta-42"}


def seal(data: bytes) -> bytes:
    return b"S" + bytes(b ^ 0x5A for b in data)


def unseal(data: bytes) -> bytes:
    if not data.startswith(b"S"):
        raise OSError("dpapi")
    return bytes(b ^ 0x5A for b in data[1:])


class VaultTest(unittest.TestCase):
    def test_password_is_sealed_and_bound_to_its_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Vault(Path(tmp) / "smb.bin", seal, unseal)
            self.assertTrue(vault.update(AUTH))
            self.assertFalse(vault.update(AUTH))
            self.assertNotIn(b"Batteria", (Path(tmp) / "smb.bin").read_bytes())
            login = vault.login("smb://NAS/condivisa/")
            self.assertEqual((login.user, login.password), ("nuxiva-share", "Batteria-Corretta-42"))
            self.assertNotIn("Batteria", repr(login))
            self.assertIsNone(vault.login("smb://altro/condivisa"))
            self.assertTrue(vault.update({}))
            self.assertIsNone(vault.login("smb://nas/condivisa"))

    def test_hostile_credentials_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Vault(Path(tmp) / "smb.bin", seal, unseal)
            for bad in ({**AUTH, "user": "a b"}, {**AUTH, "password": "x\n"}, {**AUTH, "password": ""},
                        {**AUTH, "target": "smb://h/../x"}, {**AUTH, "password": "x" * 300}, {**AUTH, "target": "\\\\h\\s"}):
                with self.assertRaises(CredentialError):
                    vault.update(bad)
            self.assertFalse((Path(tmp) / "smb.bin").exists())


class SmbAuthTest(unittest.TestCase):
    def test_error_codes_are_classified(self):
        smbauth.classify(0)
        smbauth.classify(1219)
        with self.assertRaises(sink.AuthError):
            smbauth.classify(1326)
        with self.assertRaises(sink.UnreachableError):
            smbauth.classify(53)
        with self.assertRaises(sink.SinkError):
            smbauth.classify(9999)


class HotkeyTest(unittest.TestCase):
    def test_only_the_real_print_screen_key_fires_on_release(self):
        vk = hotkey.VK_SNAPSHOT
        self.assertEqual(hotkey.decide(0, hotkey.WM_KEYDOWN, vk, 0), (False, True))
        self.assertEqual(hotkey.decide(0, hotkey.WM_KEYUP, vk, 0), (True, True))
        self.assertEqual(hotkey.decide(0, hotkey.WM_SYSKEYUP, vk, 0), (True, True))
        self.assertEqual(hotkey.decide(0, hotkey.WM_KEYUP, 0x41, 0), (False, False))
        self.assertEqual(hotkey.decide(0, hotkey.WM_KEYUP, vk, hotkey.LLKHF_INJECTED), (False, False))
        self.assertEqual(hotkey.decide(-1, hotkey.WM_KEYUP, vk, 0), (False, False))


class ClipboardTest(unittest.TestCase):
    def test_dib_has_no_file_header(self):
        from PIL import Image
        data = clipboard.dib(Image.new("RGB", (4, 2)))
        self.assertEqual(int.from_bytes(data[:4], "little"), 40)


class IntentTest(unittest.TestCase):
    def test_screenshot_requests_in_every_language(self):
        for text in ("fai uno screenshot di quello che vedi", "Fammi uno screenshot", "cattura lo schermo",
                     "screenshot", "salva una schermata", "take a screenshot", "fais une capture d'écran",
                     "haz una captura de pantalla", "Nuxiva, scatta uno screenshot per favore"):
            self.assertTrue(shot.asks(text), text)

    def test_other_sentences_are_not_screenshots(self):
        for text in ("come si fa uno screenshot?", "how do I take a screenshot", "cosa vedi sullo schermo?",
                     "aprimi il sito example.com", "leggi questo documento", "", "fai " + "x" * 400 + " screenshot"):
            self.assertFalse(shot.asks(text), text)


class AuthenticatedDeliveryTest(unittest.TestCase):
    def make(self, tmp, connect):
        notes = []
        vault = Vault(Path(tmp) / "smb.bin", seal, unseal)
        service = Service(Path(tmp) / "q", lambda text, tone: notes.append((text, tone)),
                          lambda key, **values: key, Path(tmp) / "guests", vault=vault, connect=connect)
        service.apply({"NUXIVA_SCREENSHOT": "1", "NUXIVA_SCREENSHOT_TARGET": "smb://nas/condivisa"}, AUTH)
        return service, notes

    def test_wrong_password_is_reported_and_the_capture_stays_queued(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            connect = mock.Mock(side_effect=sink.AuthError("auth:1326"))
            service, notes = self.make(tmp, connect)
            with mock.patch("screenshot.service.capture.grab", return_value=Image.new("RGB", (8, 8))):
                self.assertEqual(service.capture_once(locked=False), "queued")
            connect.assert_called_once_with("\\\\nas\\condivisa", "nuxiva-share", "Batteria-Corretta-42")
            self.assertEqual(notes, [("screenshot.auth_failed", "error")])
            self.assertEqual(len(service.spool.pending()), 1)

    def test_queue_is_delivered_when_the_share_comes_back(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            connect = mock.Mock(side_effect=[sink.UnreachableError("network:53"), None])
            service, notes = self.make(tmp, connect)
            share = Path(tmp) / "share"
            share.mkdir()
            with mock.patch("screenshot.service.capture.grab", return_value=Image.new("RGB", (8, 8))), \
                    mock.patch.object(Service, "directory", return_value=sink.resolve(share, "05 Scambio/Screenshot")):
                self.assertEqual(service.capture_once(locked=False), "queued")
                service.spool.next_try = 0.0
                self.assertEqual(service.retry(), 1)
            self.assertEqual(notes, [("screenshot.queued", "warn"), ("screenshot.delivered_later", "ok")])
            stored = list((share / "05 Scambio" / "Screenshot").iterdir())
            self.assertEqual(len(stored), 1)
            self.assertEqual(Image.open(io.BytesIO(stored[0].read_bytes())).size, (8, 8))

    def test_display_path_and_clipboard_copy(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            copied = []
            service = Service(Path(tmp) / "q", lambda text, tone: None, lambda key, **values: key,
                              Path(tmp) / "guests", clipboard=copied.append)
            service.apply({"NUXIVA_SCREENSHOT": "1", "NUXIVA_SCREENSHOT_TARGET": "smb://nas/condivisa"})
            self.assertEqual(service.display(), "\\\\nas\\condivisa\\05 Scambio\\Screenshot")
            with mock.patch("screenshot.service.capture.grab", return_value=Image.new("RGB", (8, 8))), \
                    mock.patch.object(Service, "directory", side_effect=sink.SinkError("down")):
                outcome = service.shoot(locked=False)
            self.assertEqual((outcome.status, outcome.key), ("queued", "screenshot.queued"))
            self.assertEqual(len(copied), 1)


if __name__ == "__main__":
    unittest.main()
