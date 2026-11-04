import json
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "client_web/src"


def panel_ids() -> set[str]:
    text = (SRC / "core_apps/GlobalCommandGrid.tsx").read_text(encoding="utf-8")
    return set(re.findall(r"\{ id: '([a-z0-9_]+)', iconName", text))


def known_apps() -> set[str]:
    text = (SRC / "app_shell/window_manager/app_scanner.ts").read_text(encoding="utf-8")
    block = re.search(r"KNOWN_APPLICATION_IDS = new Set\(\[(.*?)\]\)", text, re.S).group(1)
    return set(re.findall(r"'([a-z0-9_]+)'", block))


def app_manifests() -> set[str]:
    found = set()
    for path in SRC.glob("**/manifest.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("kind") == "app" or str(data.get("scope", "")).startswith("apps/"):
            found.add(data["id"])
    return found


class SectionsTest(unittest.TestCase):
    def test_panel_holds_no_application(self):
        apps = known_apps() | app_manifests()
        self.assertEqual(panel_ids() & apps, set())

    def test_every_panel_entry_has_a_view_and_texts(self):
        for ident in panel_ids():
            self.assertTrue((SRC / "core_apps" / ident / "View.tsx").is_file(), ident)
            self.assertTrue((SRC / "core_apps" / ident / "language/it.json").is_file(), ident)

    def test_every_application_has_texts(self):
        for path in SRC.glob("apps/*/manifest.json"):
            self.assertTrue((path.parent / "language/it.json").is_file(), path.parent.name)


if __name__ == "__main__":
    unittest.main()
