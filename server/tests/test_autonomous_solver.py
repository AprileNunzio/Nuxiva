import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

from server.features.autonomous_solver.log_diagnostics import log_diagnostic_engine
from server.features.autonomous_solver.models import (
    AttemptRecord,
    AutonomousSolveRequest,
    CommandStep,
    ExecutionPlan,
    ScriptArtifact,
    TargetOS,
)
from server.features.autonomous_solver.solver_engine import UniversalAutonomousSolver
from server.cmd.route_scanner import route_scanner


class TestUniversalAutonomousSolver(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_cross_os_log_diagnostics(self):
        py_diag = log_diagnostic_engine.analyze(
            "python3 app.py", 1, "", "ModuleNotFoundError: No module named 'paramiko'"
        )
        self.assertEqual(py_diag[0].category, "missing_python_module")
        self.assertEqual(py_diag[0].extracted_symbol, "paramiko")

        win_diag = log_diagnostic_engine.analyze(
            "foo.exe", 1, "", "'foo.exe' is not recognized as an internal or external command"
        )
        self.assertEqual(win_diag[0].category, "missing_binary")
        self.assertEqual(win_diag[0].extracted_symbol, "foo.exe")

        perm_diag = log_diagnostic_engine.analyze("./run.sh", 126, "", "bash: ./run.sh: Permission denied")
        self.assertEqual(perm_diag[0].category, "permission_denied")

    def test_multi_script_execute_analyze_heal_and_verify_loop(self):
        """
        Verifica il ciclo autonomo completo:
        1) Crea 2 script (helper.py rotto + runner.py).
        2) Esegue -> fallisce con ZeroDivisionError.
        3) Analizza i log -> diagnostica script_error.
        4) Auto-ripara helper.py -> riesegue -> verifica output OK.
        """
        async def custom_healer(
            req: AutonomousSolveRequest,
            resolved_os: TargetOS,
            plan: ExecutionPlan,
            failed: AttemptRecord,
        ):
            self.assertTrue(any(d.category == "script_error" for d in failed.diagnostics))
            healed = plan.model_copy(deep=True)
            for script in healed.scripts:
                if script.filename == "helper.py":
                    script.content = "def compute(a, b):\n    return a // max(b, 1)\n"
            return healed, "Patch automatica applicata a helper.py per evitare ZeroDivisionError."

        solver = UniversalAutonomousSolver(
            runs_dir=Path(self._tmpdir.name),
            healer_fn=custom_healer,
        )

        initial_plan = ExecutionPlan(
            summary="Pipeline multi-script con errore intenzionale al tentativo 1",
            scripts=[
                ScriptArtifact(
                    filename="helper.py",
                    language="python",
                    content="def compute(a, b):\n    return a // b\n",
                    purpose="Funzione di calcolo ausiliaria",
                ),
                ScriptArtifact(
                    filename="runner.py",
                    language="python",
                    content="from helper import compute\nprint('RESULT=' + str(compute(42, 0)))\n",
                    purpose="Script principale che invoca helper.py",
                ),
            ],
            commands=[
                CommandStep(
                    step_id="run_pipeline",
                    description="Esegue runner.py",
                    command=f"{sys.executable} runner.py",
                    verify_stdout_contains="RESULT=42",
                )
            ],
        )

        res = asyncio.run(
            solver.solve(
                AutonomousSolveRequest(
                    goal="Esegui calcolo sicuro multi-script",
                    max_iterations=3,
                    initial_plan=initial_plan,
                )
            )
        )

        self.assertTrue(res.success)
        self.assertEqual(res.iterations_used, 2)
        self.assertFalse(res.attempts[0].succeeded)
        self.assertIn("helper.py", res.attempts[0].healing_action)
        self.assertTrue(res.attempts[1].succeeded)
        self.assertIn("RESULT=42", res.final_output)

    def test_safety_guard_blocks_destructive_command(self):
        solver = UniversalAutonomousSolver(runs_dir=Path(self._tmpdir.name))
        dangerous_plan = ExecutionPlan(
            summary="Dangerous test",
            commands=[CommandStep(step_id="bad", command="rm -rf /")],
        )
        res = asyncio.run(
            solver.solve(
                AutonomousSolveRequest(
                    goal="Test blocco comando distruttivo",
                    max_iterations=1,
                    initial_plan=dangerous_plan,
                )
            )
        )
        self.assertFalse(res.success)
        self.assertEqual(res.attempts[0].diagnostics[0].category, "safety_violation")

    def test_solver_router_auto_discovered(self):
        prefixes = {r.prefix for r in route_scanner.scan_routers()}
        self.assertIn("/autonomous-solver", prefixes)


if __name__ == "__main__":
    unittest.main()
