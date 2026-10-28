import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from server.features.embodied_cortex.controller import router as embodied_router
from server.features.embodied_cortex.schemas import (
    ActiveInferenceStepRequest,
    ConsolidateShortcutRequest,
    QuadraticSolveRequest,
)
from server.features.embodied_cortex.service import build_embodied_cortex_service
from server.shared.errors.global_handler import register_global_error_handlers
from server.tests.cortex_support import asgi_get, requires_native


@requires_native
class EmbodiedCortexTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.service = build_embodied_cortex_service(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_hierarchical_tiers_solve_and_save_steps(self) -> None:
        proc = self.service.solve_quadratic(
            QuadraticSolveRequest(
                column_id="col_algebra_sym",
                a=1.0,
                b=-5.0,
                c=4.0,
                tier="procedural",
            )
        )
        self.assertTrue(proc.is_ok)
        self.assertEqual(proc.value["selected_tier"], "procedural")
        self.assertEqual(proc.value["roots"], [1.0, 4.0])
        self.assertEqual(proc.value["steps_executed"], 14)

        canon = self.service.solve_quadratic(
            QuadraticSolveRequest(
                column_id="col_algebra_sym",
                a=1.0,
                b=-5.0,
                c=4.0,
                tier="canonical",
            )
        )
        self.assertTrue(canon.is_ok)
        self.assertEqual(canon.value["selected_tier"], "canonical")
        self.assertEqual(canon.value["roots"], [1.0, 4.0])
        self.assertEqual(canon.value["steps_executed"], 5)

        inv = self.service.solve_quadratic(
            QuadraticSolveRequest(
                column_id="col_algebra_sym",
                a=1.0,
                b=-5.0,
                c=4.0,
                tier="invariant",
            )
        )
        self.assertTrue(inv.is_ok)
        self.assertEqual(inv.value["selected_tier"], "invariant")
        self.assertEqual(inv.value["roots"], [1.0, 4.0])
        self.assertEqual(inv.value["steps_executed"], 1)
        self.assertEqual(inv.value["steps_saved"], 13)

    def test_general_quadratic_auto_consolidates_shortcut(self) -> None:
        first = self.service.solve_quadratic(
            QuadraticSolveRequest(
                column_id="col_algebra_sym",
                a=2.0,
                b=-7.0,
                c=3.0,
                tier="invariant",
            )
        )
        self.assertTrue(first.is_ok)
        self.assertEqual(first.value["roots"], [0.5, 3.0])

        second = self.service.solve_quadratic(
            QuadraticSolveRequest(
                column_id="col_algebra_sym",
                a=2.0,
                b=-7.0,
                c=3.0,
                tier="invariant",
            )
        )
        self.assertTrue(second.is_ok)
        self.assertEqual(second.value["selected_tier"], "invariant")
        self.assertEqual(second.value["steps_executed"], 2)

    def test_consolidate_shortcut_signs_with_ed25519(self) -> None:
        res = self.service.consolidate_shortcut(
            ConsolidateShortcutRequest(
                pattern_signature="custom_harmonic_invariant",
                a=1.0,
                b=-6.0,
                c=8.0,
            )
        )
        self.assertTrue(res.is_ok)
        self.assertEqual(res.value["id"], "inv_custom_harmonic_invariant")
        self.assertIn("ed25519_signature_hex", res.value)

    def test_humanoid_active_inference_and_safety_envelope(self) -> None:
        step = self.service.step_active_inference(
            ActiveInferenceStepRequest(
                joint_id="hip_pitch_l",
                target_angle_rad=0.35,
                feedforward_torque_nm=25.0,
                dt_sec=0.02,
                measured_load_kg=2.0,
            )
        )
        self.assertTrue(step.is_ok)
        self.assertEqual(step.value["joint_id"], "hip_pitch_l")
        self.assertGreater(step.value["zmp_stability_margin_m"], 0.0)

        out_of_bounds = self.service.step_active_inference(
            ActiveInferenceStepRequest(
                joint_id="hip_pitch_l",
                target_angle_rad=2.80,
                feedforward_torque_nm=25.0,
                dt_sec=0.02,
                measured_load_kg=1.0,
            )
        )
        self.assertFalse(out_of_bounds.is_ok)
        self.assertEqual(out_of_bounds.error.code, "cortex.embodied.joint_limit_exceeded")

    def test_encrypted_persistence_round_trip(self) -> None:
        self.service.solve_quadratic(
            QuadraticSolveRequest(
                column_id="col_algebra_sym",
                a=1.0,
                b=0.0,
                c=-9.0,
                tier="invariant",
            )
        )
        reloaded = build_embodied_cortex_service(Path(self._tmp.name))
        overview = reloaded.overview()
        self.assertTrue(overview.is_ok)
        self.assertGreaterEqual(
            overview.value["cortical"]["columns"][0]["total_executions"],
            13,
        )

    def test_http_overview_endpoint(self) -> None:
        app = FastAPI()
        register_global_error_handlers(app)
        app.include_router(embodied_router, prefix="/api/v1")
        status, body = asgi_get(app, "/api/v1/cognitive/embodied-cortex/overview")
        self.assertEqual(status, 200)
        self.assertIn("cortical", body)
        self.assertIn("embodied", body)
        self.assertIn("metrics", body)


if __name__ == "__main__":
    unittest.main()
