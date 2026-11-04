import unittest
import asyncio
from server.features.presence_privacy.vision_telemetry import (
    VisionTelemetryManager,
    VisionTelemetryPayload,
    EyeGazeState,
    HandGestureState,
    VisionTelemetryConfig,
)
from server.features.presence_privacy.presence_service import presence_service

class VisionTelemetryTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.manager = VisionTelemetryManager()
        self.manager.config = VisionTelemetryConfig(
            hand_gestures_enabled=True,
            gaze_tracking_enabled=True,
            auto_lock_on_looking_away_sec=0.1,  # short for test
            drowsiness_warning_enabled=True,
            gesture_sensitivity=0.6,
        )

    async def test_eye_gaze_engaged_verifies_presence(self):
        payload = VisionTelemetryPayload(
            eye_gaze=EyeGazeState(
                is_looking_at_screen=True,
                gaze_direction="center",
                eyes_closed=False,
                attention_score=0.95
            ),
            hand_gesture=HandGestureState(gesture_name="none")
        )
        res = await self.manager.process_telemetry(payload)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["presence_verified"])
        status = presence_service.get_status()
        self.assertTrue(status.is_biometrically_verified)
        self.assertTrue(status.is_owner_approaching)

    async def test_eye_gaze_looking_away_triggers_auto_lock(self):
        # 1. Start engaged
        await self.manager.process_telemetry(VisionTelemetryPayload(
            eye_gaze=EyeGazeState(is_looking_at_screen=True)
        ))
        self.assertTrue(presence_service.get_status().is_biometrically_verified)

        # 2. Look away start
        await self.manager.process_telemetry(VisionTelemetryPayload(
            eye_gaze=EyeGazeState(is_looking_at_screen=False, gaze_direction="right")
        ))
        # Wait for timeout
        await asyncio.sleep(0.15)

        # 3. Next telemetry triggers auto-lock
        res = await self.manager.process_telemetry(VisionTelemetryPayload(
            eye_gaze=EyeGazeState(is_looking_at_screen=False, gaze_direction="right")
        ))
        self.assertIn("AUTO_LOCK_TRIGGERED", res["actions"])
        self.assertFalse(res["presence_verified"])
        self.assertFalse(presence_service.get_status().is_biometrically_verified)

    async def test_drowsiness_warning(self):
        payload = VisionTelemetryPayload(
            eye_gaze=EyeGazeState(
                is_looking_at_screen=True,
                eyes_closed=True,
                drowsiness_alert=True
            )
        )
        res = await self.manager.process_telemetry(payload)
        self.assertIn("DROWSINESS_WARNING", res["actions"])

    async def test_hand_fist_triggers_immediate_privacy_lock(self):
        # First ensure verified
        presence_service.set_presence(approaching=True, verified=True, user="owner")
        self.assertTrue(presence_service.get_status().is_biometrically_verified)

        payload = VisionTelemetryPayload(
            eye_gaze=EyeGazeState(is_looking_at_screen=True),
            hand_gesture=HandGestureState(
                gesture_name="fist",
                confidence=0.88,
                hand_detected=True,
                hand_count=1
            )
        )
        res = await self.manager.process_telemetry(payload)
        self.assertIn("GESTURE_FIST", res["actions"])
        self.assertIn("IMMEDIATE_PRIVACY_LOCK", res["actions"])
        self.assertFalse(presence_service.get_status().is_biometrically_verified)

    async def test_hand_swipe_gesture_triggers_action(self):
        payload = VisionTelemetryPayload(
            eye_gaze=EyeGazeState(is_looking_at_screen=True),
            hand_gesture=HandGestureState(
                gesture_name="swipe_left",
                confidence=0.82,
                hand_detected=True,
                hand_count=1
            )
        )
        res = await self.manager.process_telemetry(payload)
        self.assertIn("GESTURE_SWIPE_LEFT", res["actions"])
        self.assertEqual(res["total_gestures"], 1)

    def test_config_update(self):
        new_cfg = VisionTelemetryConfig(
            hand_gestures_enabled=False,
            gesture_sensitivity=0.9
        )
        updated = self.manager.update_config(new_cfg)
        self.assertFalse(updated.hand_gestures_enabled)
        self.assertEqual(updated.gesture_sensitivity, 0.9)

if __name__ == "__main__":
    unittest.main()
