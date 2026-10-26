import re
import tempfile
import unittest
from pathlib import Path

from features.google import cmd_mail
from features.google.commands import match
from features.people.photos import clear_samples

ROOT = Path(__file__).resolve().parents[2]


class MailDownloadTest(unittest.TestCase):
    def test_bills_request_routes_to_download(self):
        text = "controlla nella mail tutte le bollette di Octopus e scaricale"
        self.assertEqual(match(text), ("mail_download", "gmail"))
        query, folder = cmd_mail.attachment_request(text)
        self.assertEqual(query, "bollette Octopus has:attachment filename:pdf")
        self.assertEqual(folder, "bollette-octopus")

    def test_explicit_folder_is_slugged(self):
        query, folder = cmd_mail.attachment_request("scarica gli allegati della mail di Enel nella cartella ../Luce!")
        self.assertEqual(folder, "luce")
        self.assertIn("Enel", query)

    def test_followup_question_is_not_a_command(self):
        self.assertIsNone(match("le stai scaricando?"))

    def test_file_names_are_sanitised(self):
        self.assertEqual(cmd_mail._safe_name("../../Fattura Ottobre.PDF"), "fattura-ottobre.pdf")


class FaceSamplesTest(unittest.TestCase):
    def test_clear_samples_removes_embeddings_only(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            for name in ("embeddings.npy", "embeddings_ir.npy", "photo.jpg"):
                (folder / name).write_bytes(b"x")
            self.assertEqual(clear_samples(folder), 2)
            self.assertTrue((folder / "photo.jpg").exists())
            self.assertFalse((folder / "embeddings.npy").exists())


class ScriptRegressionTest(unittest.TestCase):
    def test_voicestudio_never_inspects_without_type(self):
        text = (ROOT / "scripts/os/steps/66-voicestudio.sh").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"docker inspect\b", text))

    def test_ear_unit_sets_backend_path(self):
        text = (ROOT / "scripts/os/systemd/nuxiva-ear.service").read_text(encoding="utf-8")
        self.assertIn("PYTHONPATH=/opt/Nuxiva/installer_wizard/backend", text)

    def test_display_uses_proxy_on_http(self):
        text = (ROOT / "installer_wizard/web/display/ear.js").read_text(encoding="utf-8")
        self.assertNotIn(":8093", text)
