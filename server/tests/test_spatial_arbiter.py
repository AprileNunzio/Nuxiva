import unittest
from server.core.spatial_webos import (
    ArbitrationAction,
    AssistantMorphology,
    AssistantRequirement,
    ContextManifest,
    FocusLockLevel,
    GpuLoad,
    NotificationEvent,
    NotificationPriority,
    SafeZone,
    SpatialWebOSEngine,
    ViewportMode,
    VoiceInteraction,
)


class TestSpatialWebOS(unittest.TestCase):
    def setUp(self):
        self.engine = SpatialWebOSEngine()
        self.chess_manifest = ContextManifest(
            context_id="app.nuxiva.chess",
            viewport_mode=ViewportMode.IMMERSIVE_STAGE,
            gpu_load=GpuLoad.MEDIUM,
            assistant_requirement=AssistantRequirement(
                preferred_morphology=AssistantMorphology.FLOATING_ORB,
                fallback_morphology=AssistantMorphology.AMBIENT_STREAM,
                allowed_safe_zones=[SafeZone.TOP_RIGHT, SafeZone.BOTTOM_RIGHT],
                voice_interaction=VoiceInteraction.CONTINUOUS_CO_PILOT,
            ),
            focus_lock_level=FocusLockLevel.LOCK_2_ENGAGED,
        )
        self.cad_manifest = ContextManifest(
            context_id="app.nuxiva.cad3d",
            viewport_mode=ViewportMode.IMMERSIVE_STAGE,
            gpu_load=GpuLoad.HIGH,
            assistant_requirement=AssistantRequirement(
                preferred_morphology=AssistantMorphology.AMBIENT_STREAM,
                fallback_morphology=AssistantMorphology.AMBIENT_STREAM,
                allowed_safe_zones=[],
                voice_interaction=VoiceInteraction.CONTINUOUS_CO_PILOT,
            ),
            focus_lock_level=FocusLockLevel.LOCK_3_IMMERSIVE,
        )

    def test_p0_critical_preemption(self):
        event = NotificationEvent(
            id="evt-smoke",
            priority=NotificationPriority.P0_CRITICAL,
            title_key="alarm_fire",
            message_key="sensor_smoke",
            source_module="sensor.smoke",
            timestamp_ms=1000,
        )
        res = self.engine.arbitrate(event, self.chess_manifest)
        self.assertEqual(res.action, ArbitrationAction.PREEMPTION_TOTAL)
        self.assertTrue(res.suspend_primary_stage)
        self.assertEqual(res.target_layer, "Z4CriticalInterrupt")
        self.assertFalse(res.should_defer)
        self.assertEqual(res.reason_code, "p0_preemption")

    def test_p1_intercom_smart_pip_vs_voice_interject(self):
        event = NotificationEvent(
            id="evt-intercom",
            priority=NotificationPriority.P1_HIGH,
            title_key="intercom_ring",
            message_key="doorbell_event",
            source_module="intercom",
            timestamp_ms=1001,
        )
        res_chess = self.engine.arbitrate(event, self.chess_manifest)
        self.assertEqual(res_chess.action, ArbitrationAction.SMART_PIP)
        self.assertEqual(res_chess.assigned_safe_zone, SafeZone.TOP_RIGHT)
        self.assertFalse(res_chess.suspend_primary_stage)

        res_cad = self.engine.arbitrate(event, self.cad_manifest)
        self.assertEqual(res_cad.action, ArbitrationAction.VOICE_INTERJECT)
        self.assertEqual(res_cad.target_morphology, AssistantMorphology.AMBIENT_STREAM)

    def test_p2_render_deferred_in_game_and_cad(self):
        event = NotificationEvent(
            id="evt-render",
            priority=NotificationPriority.P2_NORMAL,
            title_key="render_done",
            message_key="mesh_exported",
            source_module="blender",
            timestamp_ms=1002,
        )
        res_chess = self.engine.arbitrate(event, self.chess_manifest)
        self.assertEqual(res_chess.action, ArbitrationAction.DEFERRAL)
        self.assertTrue(res_chess.should_defer)

        idle_manifest = ContextManifest.idle_default()
        res_idle = self.engine.arbitrate(event, idle_manifest)
        self.assertEqual(res_idle.action, ArbitrationAction.SMART_PIP)
        self.assertFalse(res_idle.should_defer)

    def test_deferred_drain_lifecycle(self):
        event = NotificationEvent(
            id="evt-backup",
            priority=NotificationPriority.P2_NORMAL,
            title_key="backup_done",
            message_key="status_ok",
            source_module="backup",
            timestamp_ms=1003,
        )
        self.engine.arbitrate(event, self.chess_manifest)
        drained = self.engine.drain_deferred()
        self.assertEqual(len(drained), 1)
        self.assertEqual(drained[0].title_key, "backup_done")

    def test_intent_router_resolutions(self):
        self.assertEqual(self.engine.resolve_intent("voice_trigger_chess"), "app.nuxiva.chess")
        self.assertEqual(self.engine.resolve_intent("voice_trigger_cad3d"), "app.nuxiva.cad3d")
        self.assertEqual(self.engine.resolve_intent("voice_trigger_idle"), "app.nuxiva.idle")
        self.assertEqual(self.engine.resolve_intent("voice_trigger_whisper"), "app.nuxiva.whisper")
        self.assertIsNone(self.engine.resolve_intent("unrecognized_input"))


if __name__ == "__main__":
    unittest.main()
