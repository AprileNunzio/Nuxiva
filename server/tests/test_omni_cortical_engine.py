import unittest
from server.features.llm_gateway.contracts import CognitiveEngineVersion
from server.core.reasoning.engines.scanner import EngineScanner
from server.features.brain.service import BrainEngineService
from server.core.reasoning.omni_cortical_engine import OmniCorticalEngine, LatentSpikePacket
from server.core.orchestrator.system1_router import System1Router

class OmniCorticalEngineTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.scanner = EngineScanner()
        self.service = BrainEngineService()
        self.router = System1Router()
        self.engine = OmniCorticalEngine()

    def test_scanner_discovers_all_engines(self) -> None:
        engines = self.scanner.list_engines()
        self.assertGreaterEqual(len(engines), 6)
        versions = {e.version for e in engines}
        self.assertIn(CognitiveEngineVersion.LEGACY_4_2, versions)
        self.assertIn(CognitiveEngineVersion.VELOCE_5_0, versions)
        self.assertIn(CognitiveEngineVersion.EMPATICO_5_0, versions)
        self.assertIn(CognitiveEngineVersion.PRO_6_0, versions)
        self.assertIn(CognitiveEngineVersion.ULTRA_6_5, versions)
        self.assertIn(CognitiveEngineVersion.AUTO_6_5, versions)

    def test_service_engine_switch(self) -> None:
        status_auto = self.service.get_status()
        self.assertTrue(status_auto.success)
        self.assertEqual(status_auto.current_configured, CognitiveEngineVersion.AUTO_6_5)

        status_ultra = self.service.switch_engine(CognitiveEngineVersion.ULTRA_6_5)
        self.assertEqual(status_ultra.current_configured, CognitiveEngineVersion.ULTRA_6_5)
        self.assertEqual(status_ultra.active_runtime, CognitiveEngineVersion.ULTRA_6_5)
        self.assertEqual(status_ultra.latency_sla_ms, 650)
        self.assertEqual(status_ultra.vram_mb, 8192)

        telemetry = self.service.get_telemetry_snapshot(psi=0.88)
        self.assertEqual(telemetry.version, CognitiveEngineVersion.ULTRA_6_5)
        self.assertEqual(telemetry.complexity_psi, 0.88)

    def test_neuro_cognitive_psi_formula(self) -> None:
        psi_low = self.router.calculate_neuro_cognitive_complexity_psi(
            task_complexity=0.1, semantic_surprise=0.1, user_emotion=0.1, hardware_pressure=0.0
        )
        self.assertLess(psi_low, 0.25)
        self.assertEqual(self.router.select_engine(psi_low), CognitiveEngineVersion.VELOCE_5_0)

        psi_mid = self.router.calculate_neuro_cognitive_complexity_psi(
            task_complexity=0.4, semantic_surprise=0.3, user_emotion=0.2, hardware_pressure=0.0
        )
        self.assertGreaterEqual(psi_mid, 0.25)
        self.assertLess(psi_mid, 0.50)
        self.assertEqual(self.router.select_engine(psi_mid), CognitiveEngineVersion.EMPATICO_5_0)

        psi_pro = self.router.calculate_neuro_cognitive_complexity_psi(
            task_complexity=0.8, semantic_surprise=0.6, user_emotion=0.3, hardware_pressure=0.0
        )
        self.assertGreaterEqual(psi_pro, 0.50)
        self.assertLess(psi_pro, 0.75)
        self.assertEqual(self.router.select_engine(psi_pro), CognitiveEngineVersion.PRO_6_0)

        psi_ultra = self.router.calculate_neuro_cognitive_complexity_psi(
            task_complexity=0.95, semantic_surprise=0.9, user_emotion=0.5, hardware_pressure=0.0
        )
        self.assertGreaterEqual(psi_ultra, 0.75)
        self.assertEqual(self.router.select_engine(psi_ultra), CognitiveEngineVersion.ULTRA_6_5)

    async def test_omni_cortical_cycle_and_anomaly_recovery(self) -> None:
        res = await self.engine.execute_cognitive_cycle(
            sensory_tensor=[0.1, 0.2, 0.3], requested_ver=CognitiveEngineVersion.AUTO_6_5
        )
        self.assertTrue(res.success)
        self.assertEqual(res.active_engine, CognitiveEngineVersion.VELOCE_5_0)

        recovered = self.engine.recover_from_anomaly()
        self.assertEqual(recovered, CognitiveEngineVersion.EMPATICO_5_0)

if __name__ == "__main__":
    unittest.main()
