import unittest

from agenti.rpa import releases

BASE = f"https://github.com/{releases.REPOSITORY}/releases/download"


def release(tag, assets=(releases.INSTALLER,), **extra):
    return {"tag_name": tag, "assets": [{"name": a, "browser_download_url": f"{BASE}/{tag}/{a}"} for a in assets], **extra}


class ReleasesTest(unittest.TestCase):
    def test_the_newest_published_installer_is_chosen(self):
        chosen = releases.pick([release("assistant-v1.2.0"), release("assistant-v1.10.0"), release("v9.0.0"),
                                release("assistant-v2.0.0", draft=True), release("assistant-v3.0.0", assets=("manifest.json",))])
        self.assertEqual(chosen, f"{BASE}/assistant-v1.10.0/{releases.INSTALLER}")

    def test_the_new_installer_name_wins_over_the_legacy_one(self):
        both = release("assistant-v5.8.1", assets=(releases.LEGACY_INSTALLER, releases.INSTALLER))
        info = releases.newest([both])
        self.assertEqual((info["name"], info["version"]), (releases.INSTALLER, "5.8.1"))

    def test_legacy_installer_is_still_offered_when_it_is_the_only_one(self):
        info = releases.newest([release("assistant-v5.3.0", assets=(releases.LEGACY_INSTALLER,))])
        self.assertEqual(info["name"], releases.LEGACY_INSTALLER)

    def test_no_installer_means_no_redirect(self):
        self.assertEqual(releases.pick([release("v1.0.0")]), "")

    def test_foreign_download_hosts_are_rejected(self):
        foreign = {"tag_name": "assistant-v9.0.0", "assets": [{"name": releases.INSTALLER, "browser_download_url": "https://evil.example/x.exe"}]}
        self.assertEqual(releases.pick([foreign]), "")

    def test_enrollment_only_selects_a_compatible_official_release_with_signature(self):
        unsigned = release("assistant-v5.3.1")
        self.assertEqual(releases.pick([unsigned], enrolled=True), "")
        signed = release("assistant-v5.3.1", assets=(releases.INSTALLER, "manifest.json", "manifest.sig"))
        self.assertEqual(releases.pick([signed], enrolled=True), f"{BASE}/assistant-v5.3.1/{releases.INSTALLER}")


if __name__ == "__main__":
    unittest.main()
