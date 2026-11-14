import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import runtime_check
from tests.packaging_helpers import load

ROOT = Path(__file__).resolve().parent.parent


def build_tree(base: Path, themes=runtime_check.THEMES, fonts=True) -> Path:
    root = base / "customtkinter"
    (root / "assets" / "themes").mkdir(parents=True)
    for name in themes:
        (root / "assets" / "themes" / name).write_text("{}", encoding="utf-8")
    if fonts:
        (root / "assets" / "fonts").mkdir(parents=True)
        (root / "assets" / "fonts" / "Roboto.ttf").write_bytes(b"0")
    return root


class MissingAssetsTest(unittest.TestCase):
    def test_complete_tree_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(runtime_check.missing_assets(build_tree(Path(tmp))), [])

    def test_missing_theme_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_tree(Path(tmp), themes=("dark-blue.json", "green.json"))
            self.assertEqual(runtime_check.missing_assets(root), ["assets/themes/blue.json"])

    def test_missing_fonts_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(runtime_check.missing_assets(build_tree(Path(tmp), fonts=False)), ["assets/fonts"])

    def test_missing_package_is_reported(self):
        self.assertEqual(runtime_check.missing_assets(None), ["customtkinter"])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(runtime_check.missing_assets(Path(tmp) / "absent"), ["customtkinter"])

    def test_installed_toolkit_is_complete(self):
        self.assertEqual(runtime_check.missing_assets(runtime_check.toolkit_root()), [])


class EnsureTest(unittest.TestCase):
    def test_missing_assets_give_clear_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(runtime_check, "toolkit_root", return_value=Path(tmp) / "customtkinter"):
                self.assertEqual(runtime_check.ensure(interactive=False), runtime_check.EXIT_ASSETS)


class VerifyBundleTest(unittest.TestCase):
    def test_exit_codes(self):
        verify = load("verify_bundle")
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp)
            self.assertEqual(verify.main(["verify_bundle.py", str(dist)]), 1)
            build_tree(dist / "_internal")
            self.assertEqual(verify.main(["verify_bundle.py", str(dist)]), 0)
        self.assertEqual(verify.main(["verify_bundle.py"]), 2)


class MessagesTest(unittest.TestCase):
    def test_startup_messages_exist_in_every_language(self):
        for language in ("it", "en", "fr", "es"):
            table = json.loads((ROOT / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
            self.assertIn("{files}", table["startup.assets_missing"])
            self.assertIn("{reason}", table["startup.toolkit_failed"])


class SpecTest(unittest.TestCase):
    def test_spec_bundles_toolkit_data(self):
        text = (ROOT / "packaging" / "nuxiva_assistant.spec").read_text(encoding="utf-8")
        self.assertIn('"customtkinter"', text)
        self.assertIn("collect_all", text)

    def test_build_runs_verification_and_smoke_test(self):
        text = (ROOT / "packaging" / "build.ps1").read_text(encoding="utf-8")
        self.assertIn("verify_bundle.py", text)
        self.assertIn("--smoke-test", text)


if __name__ == "__main__":
    unittest.main()
