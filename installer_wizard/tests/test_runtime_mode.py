import ast
import unittest
from pathlib import Path
from unittest import mock

import brain_intent
import config
import packages
from state import store

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "installer_wizard" / "backend" / "config.py"
SKIP = {"node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__", ".git"}


def _python_files():
    for path in REPO.rglob("*.py"):
        if not SKIP.intersection(path.relative_to(REPO).parts):
            yield path


def _demo_literals(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id == "DEMO" for t in targets) and isinstance(value, ast.Constant):
            yield node.lineno, value.value


class RuntimeModeTest(unittest.TestCase):
    def test_demo_mode_is_off_in_the_single_source_of_truth(self):
        self.assertIs(config.DEMO, False)
        self.assertEqual([v for _, v in _demo_literals(SOURCE)], [False])

    def test_no_module_hardcodes_its_own_demo_flag(self):
        offenders = [f"{path.relative_to(REPO)}:{line}={value!r}"
                     for path in _python_files() if path != SOURCE
                     for line, value in _demo_literals(path)]
        self.assertEqual(offenders, [])

    def test_runtime_modules_share_the_config_flag(self):
        self.assertIs(packages.DEMO, config.DEMO)

    def test_store_sees_an_external_ollama_used_as_cloud_reserve(self):
        package = packages.PACKAGE_BY_ID["brain_local"]
        env = {"NUXIVA_BRAIN": "cloud", "NUXIVA_LLM_CODER_ORDER": "cloud:gemini/gemini-3.8-flash,qwen2.5:1.5b"}
        saved = store.steps.get("ollama")
        store.steps["ollama"] = {"status": "skipped"}
        self.addCleanup(lambda: store.steps.__setitem__("ollama", saved) if saved is not None else store.steps.pop("ollama", None))
        with mock.patch.object(brain_intent, "local_engine", return_value=True), \
                mock.patch.object(brain_intent, "ollama_remote", return_value=False), \
                mock.patch.object(packages, "ollama_remote", return_value=False):
            self.assertEqual(packages.state(package, env), "installed")
        with mock.patch.object(brain_intent, "local_engine", return_value=False), \
                mock.patch.object(brain_intent, "ollama_remote", return_value=False), \
                mock.patch.object(packages, "ollama_remote", return_value=False):
            self.assertNotEqual(packages.state(package, env), "installed")


if __name__ == "__main__":
    unittest.main()
