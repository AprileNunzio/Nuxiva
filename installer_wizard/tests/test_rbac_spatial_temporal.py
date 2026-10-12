import unittest
from unittest import mock
from features.authz.policy import Policy, Decision
from features.authz.principal import Principal, Strength
from features.authz.risk import Risk
from features.authz.spatial_temporal import is_time_allowed, is_zone_allowed, validate_spatial_temporal
from features.authz import resolve, heard, gate


class SpatialTemporalRBACUnitTests(unittest.TestCase):

    def test_time_window_validation(self):
        # 1700049600 is 2023-11-15 12:00:00 (midday)
        from datetime import datetime
        dt = datetime(2026, 10, 12, 12, 0)
        self.assertTrue(is_time_allowed("08:00-18:00", dt.timestamp()))
        self.assertFalse(is_time_allowed("14:00-18:00", dt.timestamp()))
        self.assertTrue(is_time_allowed("", dt.timestamp()))

    def test_zone_allowed_matching(self):
        zones = ("cucina", "salotto")
        self.assertTrue(is_zone_allowed(zones, "cucina"))
        self.assertTrue(is_zone_allowed(zones, "CUCINA"))
        self.assertFalse(is_zone_allowed(zones, "camera_padronale"))

    def test_spatial_temporal_rejects_unauthorized_room(self):
        cleaner = Principal(slug="maria", role="staff", subrole="cleaner",
                            zones=("cucina",), schedule="08:00-18:00")
        decision = validate_spatial_temporal(cleaner, device_zone="camera_padronale")
        self.assertIsNotNone(decision)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "zone")

    def test_owner_bypasses_spatial_temporal_limits(self):
        owner = Principal(slug="nunzio", role="owner", zones=("ufficio",))
        decision = validate_spatial_temporal(owner, device_zone="garage")
        self.assertIsNone(decision)

    def test_subrole_ceiling_limits(self):
        pol = Policy()
        nanny = Principal(slug="tata", role="staff", subrole="nanny", strength=Strength.STRONG)
        butler = Principal(slug="giacomo", role="staff", subrole="butler", strength=Strength.STRONG)
        self.assertEqual(pol.limit(nanny), Risk.HOME)
        self.assertEqual(pol.limit(butler), Risk.FILES)

    def test_multi_speaker_active_face_correlation(self):
        faces_list = [
            {"slug": "nunzio", "live": True, "active_speaker": False},
            {"slug": "tata", "live": True, "active_speaker": True}
        ]
        with mock.patch.object(resolve, "faces", return_value=faces_list), \
             mock.patch.object(resolve, "_profile", return_value={"slug": "nunzio", "role": "owner"}), \
             mock.patch.object(heard.heard, "verify", return_value=mock.MagicMock(slug="nunzio", score=0.9, device="mic")):
            who = resolve.for_request("kiosk", "nunzio", "apri cassaforte")
            self.assertEqual(who.strength, Strength.WEAK)


if __name__ == "__main__":
    unittest.main()
