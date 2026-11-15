import json
import unittest

from agenti.rpa import android_release, release_meta, releases

BASE = f"https://github.com/{releases.REPOSITORY}/releases/download"
TEXT = {"it": "a", "en": "b", "fr": "c", "es": "d"}


def document(**over):
    data = {
        "schema": 1, "version": "5.8.4", "tag": "v5.8.4", "title": TEXT,
        "components": {"server": {"version": "5.8.4"}, "android": {"version": "5.8.4"}, "windows": {"version": "5.8.4"}},
        "assets": [{"name": "Nuxiva.apk", "size": 10, "sha256": "ab" * 32}, {"name": "Nuxiva_Setup.exe", "size": 20, "sha256": "cd" * 32}],
        "features": [{"source": "20261115000000-x", "date": "2026-11-15", "text": TEXT}],
        "fixes": [],
    }
    data.update(over)
    return json.dumps(data).encode()


class ParseTest(unittest.TestCase):
    def test_valid_document(self):
        info = release_meta.parse(document())
        self.assertEqual((info["version"], info["tag"], len(info["features"])), ("5.8.4", "v5.8.4", 1))
        self.assertEqual(info["components"], {"server": "5.8.4", "android": "5.8.4", "windows": "5.8.4"})

    def test_misaligned_components_are_rejected(self):
        bad = {"server": {"version": "5.8.3"}, "android": {"version": "5.8.4"}, "windows": {"version": "5.8.4"}}
        with self.assertRaises(ValueError):
            release_meta.parse(document(components=bad))

    def test_invalid_shapes_are_rejected(self):
        for over in ({"schema": 2}, {"tag": "v5.8.3"}, {"title": {"it": "a"}}, {"assets": []},
                     {"assets": [{"name": "../x", "size": 1, "sha256": "ab" * 32}]},
                     {"features": [{"source": "x", "date": "d", "text": {"it": ""}}]}):
            with self.subTest(over=over), self.assertRaises(ValueError):
                release_meta.parse(document(**over))

    def test_oversized_document_is_rejected(self):
        with self.assertRaises(ValueError):
            release_meta.parse(b" " * (release_meta.MAX_BYTES + 1))


class UnifiedReleaseTest(unittest.TestCase):
    def test_one_release_serves_both_installers_and_the_notes(self):
        names = (android_release.APK, releases.INSTALLER, release_meta.NAME)
        item = {"tag_name": "v5.8.4", "assets": [
            {"name": n, "browser_download_url": f"{BASE}/v5.8.4/{n}", "digest": "sha256:" + "ab" * 32} for n in names]}
        apk = android_release.newest([item])
        self.assertEqual((apk["version"], apk["tag"], apk["notes_url"]), ("5.8.4", "v5.8.4", f"{BASE}/v5.8.4/release.json"))
        exe = releases.newest([item])
        self.assertEqual((exe["version"], exe["name"]), ("5.8.4", releases.INSTALLER))


if __name__ == "__main__":
    unittest.main()
