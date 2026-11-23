import ast
import builtins
import unittest
from pathlib import Path
from unittest import mock

from app import runtime_check
from autonomy import sapi_stt, stt

ROOT = Path(__file__).resolve().parent.parent
EXE = str(ROOT / "dist" / "Nuxiva.exe")


def frozen():
    return mock.patch.multiple(runtime_check.sys, create=True, frozen=True, executable=EXE)


class PickEngineTest(unittest.TestCase):
    def test_fallback_needs_no_import_at_runtime(self):
        real = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name.startswith("autonomy"):
                raise OSError(22, "Invalid argument", EXE)
            return real(name, *args, **kwargs)

        with mock.patch.object(stt, "available", return_value=False), mock.patch.object(builtins, "__import__", blocked):
            engine = stt.pick_engine("small", "models", False, "fr")
        self.assertIsInstance(engine, sapi_stt.SapiRecognizer)
        self.assertEqual(engine.lang, "fr")


class SpecTest(unittest.TestCase):
    def test_modules_are_not_read_back_from_the_executable(self):
        tree = ast.parse((ROOT / "packaging" / "nuxiva_assistant.spec").read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Analysis"]
        self.assertEqual(len(calls), 1)
        options = {kw.arg: kw.value for kw in calls[0].keywords}
        self.assertIs(options["noarchive"].value, True)


class GuardTest(unittest.TestCase):
    def test_unreadable_executable_is_reported(self):
        def entry():
            raise OSError(22, "Invalid argument", EXE)

        with frozen(), mock.patch.object(runtime_check, "report") as report:
            self.assertEqual(runtime_check.guard(entry), runtime_check.EXIT_BUNDLE)
        message, interactive = report.call_args.args
        self.assertIn(EXE, message)
        self.assertTrue(interactive)

    def test_other_os_errors_propagate(self):
        def entry():
            raise OSError(2, "No such file", str(ROOT / "missing.txt"))

        with frozen(), mock.patch.object(runtime_check, "report") as report, self.assertRaises(OSError):
            runtime_check.guard(entry)
        report.assert_not_called()

    def test_not_frozen_propagates(self):
        def entry():
            raise OSError(22, "Invalid argument", EXE)

        with mock.patch.object(runtime_check.sys, "frozen", False, create=True), self.assertRaises(OSError):
            runtime_check.guard(entry)

    def test_exit_code_of_entry_is_kept(self):
        self.assertEqual(runtime_check.guard(lambda: None), 0)
        self.assertEqual(runtime_check.guard(lambda: 7), 7)

    def test_every_language_explains_the_block(self):
        for lang in ("it", "en", "fr", "es"):
            text = (ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8")
            self.assertIn('"startup.bundle_unreadable"', text)


if __name__ == "__main__":
    unittest.main()
