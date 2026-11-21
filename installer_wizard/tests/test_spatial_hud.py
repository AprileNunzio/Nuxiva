import asyncio
import json
import unittest

from agenti.agent import registry
from agenti.hands import spatial_hud


class SpatialHudTest(unittest.TestCase):
    def setUp(self):
        asyncio.run(spatial_hud.spatial_hud_set_mode(False, 4))
        asyncio.run(spatial_hud.spatial_hud_set_shape("sphere"))

    def test_privacy_defaults_to_camera_off_and_local_only(self):
        snap = spatial_hud.snapshot()
        self.assertFalse(snap["camera_active"])
        self.assertTrue(snap["local_only"])
        self.assertEqual(snap["shape"], "sphere")

    def test_set_mode_and_shape_cycle(self):
        raw = asyncio.run(spatial_hud.spatial_hud_set_mode(True, 6))
        state = json.loads(raw)
        self.assertTrue(state["camera_active"])
        self.assertEqual(state["auto_close_timeout_s"], 6)

        for shape in ("torus", "cube", "helix", "dispersed", "sphere"):
            updated = json.loads(asyncio.run(spatial_hud.spatial_hud_set_shape(shape)))
            self.assertEqual(updated["shape"], shape)

        with self.assertRaises(ValueError):
            asyncio.run(spatial_hud.spatial_hud_set_shape("invalid_geometry"))

    def test_zero_trust_confirmation_gate_for_real_world_bindings(self):
        self.assertIn("spatial_hud_bind_gesture_action", registry.TOOLS)
        self.assertFalse(
            registry.needs_confirm(
                "spatial_hud_bind_gesture_action",
                {"gesture": "open_palm_disperse", "action": "view.rotate"},
            )
        )
        self.assertTrue(
            registry.needs_confirm(
                "spatial_hud_bind_gesture_action",
                {"gesture": "single_hand_focus_morph", "action": "home.light.toggle"},
            )
        )
        self.assertTrue(
            registry.needs_confirm(
                "spatial_hud_bind_gesture_action",
                {"gesture": "two_hand_pinch_stretch", "action": "system.power_off"},
            )
        )

        entry = json.loads(
            asyncio.run(
                spatial_hud.spatial_hud_bind_gesture_action(
                    "single_hand_focus_morph", "home.light.toggle"
                )
            )
        )
        self.assertTrue(entry["requires_confirmation"])

    def test_display_update_sanitizes_fields(self):
        state = spatial_hud.update_from_display(
            {
                "camera_active": True,
                "person_present": True,
                "shape": "torus",
                "active_gesture": "two_hand_pinch_stretch",
                "hands_count": 2,
                "confidence": 0.96,
            }
        )
        self.assertTrue(state["camera_active"])
        self.assertEqual(state["shape"], "torus")
        self.assertEqual(state["active_gesture"], "two_hand_pinch_stretch")
        self.assertEqual(state["hands_count"], 2)


if __name__ == "__main__":
    unittest.main()
