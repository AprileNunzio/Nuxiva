import unittest

from agenti.people import home

NOW = 1_000_000.0


def profile(slug, last_seen=0.0, first="Anna"):
    return {"slug": slug, "first_name": first, "stats": {"last_seen": last_seen}}


class HomeStatusTest(unittest.TestCase):
    def test_visible_person_is_home_via_camera(self):
        self.assertEqual(home.status(profile("anna"), "Anna Rossi", {"anna"}, NOW, [])["via"], "camera")

    def test_phone_on_wifi_keeps_person_home_without_camera(self):
        phone = {"owner": "Anna", "type": "phone", "online": True, "last_seen": NOW - 30}
        result = home.status(profile("anna", NOW - 7200), "Anna Rossi", set(), NOW, [phone])
        self.assertEqual((result["home"], result["via"]), (True, "wifi"))

    def test_phone_offline_and_no_recent_face_means_out(self):
        phone = {"owner": "anna", "type": "phone", "online": False, "last_seen": NOW - 3000}
        self.assertFalse(home.status(profile("anna", NOW - 3600), "Anna Rossi", set(), NOW, [phone])["home"])
        self.assertTrue(home.status(profile("anna", NOW - 60), "Anna Rossi", set(), NOW, [phone])["home"])

    def test_without_phone_recent_face_counts_then_expires(self):
        self.assertEqual(home.status(profile("anna", NOW - 120), "Anna Rossi", set(), NOW, [])["via"], "recent")
        self.assertFalse(home.status(profile("anna", NOW - 7200), "Anna Rossi", set(), NOW, [])["home"])

    def test_devices_of_others_or_non_personal_types_are_ignored(self):
        devices = [{"owner": "Marco", "type": "phone", "online": True}, {"owner": "Anna", "type": "tv", "online": True}]
        self.assertFalse(home.status(profile("anna", NOW - 7200), "Anna Rossi", set(), NOW, devices)["home"])


if __name__ == "__main__":
    unittest.main()
