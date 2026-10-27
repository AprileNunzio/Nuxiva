import asyncio
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from features.autonomous_worker.application.code_intel import code_intel
from features.autonomous_worker.application.workspace_runtime import workspace_runtime
from features.autonomous_worker.domain.exceptions import MissionValidationError
from features.autonomous_worker.domain.models import (
    Mission,
    MissionStatus,
    Phase,
    Task,
    TaskStatus,
)
from features.autonomous_worker.infrastructure.artifact_vault import vault
from features.autonomous_worker.infrastructure.store import MissionStore
from features.autonomous_worker.presentation.handlers import (
    apply_mission_directive,
    apply_mission_rollback,
)


class AutonomousWorkspaceRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp()).resolve()
        self.store = MissionStore(data_dir=self.temp_dir / "store")
        self.prev_root = vault.root
        vault.root = self.temp_dir / "vault"
        vault.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        vault.root = self.prev_root
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cross_file_dependency_and_contract_detection(self) -> None:
        mission = Mission(id="msn-contract-01", title="Contract Check", goal="Check imports", domain="software")
        vault.store_file(
            mission=mission,
            relative_path="billing.py",
            content="def calculate_tax(amount):\n    return amount * 0.22\n",
            generated_by="Backend Dev",
        )
        vault.store_file(
            mission=mission,
            relative_path="checkout.py",
            content="from billing import calculate_tax, missing_discount\n\ndef checkout(x):\n    return calculate_tax(x)\n",
            generated_by="Frontend Dev",
        )
        edges, warnings = code_intel.analyze_dependencies(mission)
        self.assertTrue(any(e["from"] == "checkout.py" and e["to"] == "billing.py" for e in edges))
        self.assertEqual(len(warnings), 1)
        self.assertIn("missing_discount", warnings[0])

    def test_revision_ledger_and_rollback(self) -> None:
        mission = Mission(id="msn-rev-01", title="Revisions", goal="Track history", domain="software")
        a1 = vault.store_file(mission, "engine.py", "VALUE = 1\n", "Dev")
        self.assertEqual(a1.version, 1)
        self.assertEqual(len(a1.revisions), 1)

        a2 = vault.store_file(mission, "engine.py", "VALUE = 2\n", "Dev")
        self.assertEqual(a2.version, 2)
        self.assertEqual(len(a2.revisions), 2)

        with self.assertRaises(MissionValidationError):
            vault.store_file(
                mission,
                "engine.py",
                "VALUE = 999\n",
                "Parallel Dev",
                expected_checksum=a1.checksum,
            )

        self.store.save(mission)
        with mock.patch("features.autonomous_worker.presentation.handlers.mission_store", self.store), \
             mock.patch("features.autonomous_worker.presentation.handlers.notifier.push_mission"):
            rolled = apply_mission_rollback(
                "msn-rev-01",
                {"file_path": "engine.py", "target_version": 1},
            )
            self.assertEqual(rolled["version"], 3)
            self.assertEqual(vault.read_file("msn-rev-01", "engine.py"), "VALUE = 1\n")

    def test_workspace_tools_and_sandbox_unit_test_gate(self) -> None:
        mission = Mission(id="msn-sandbox-01", title="Sandbox Gate", goal="Run real tests", domain="software")
        task = Task(id="t1", phase_id="p1", title="Math Module", description="Write math and test", specialist_role="Python Dev")

        out_write = asyncio.run(
            workspace_runtime.execute_workspace_tool(
                mission,
                task,
                "workspace_write_file",
                {"path": "calc.py", "content": "def add(a, b):\n    return a - b\n"},
            )
        )
        self.assertIn("OK: salvato calc.py", out_write)

        asyncio.run(
            workspace_runtime.execute_workspace_tool(
                mission,
                task,
                "workspace_write_file",
                {
                    "path": "test_calc.py",
                    "content": (
                        "import unittest\nfrom calc import add\n\n"
                        "class CalcTest(unittest.TestCase):\n"
                        "    def test_add(self):\n"
                        "        self.assertEqual(add(2, 3), 5)\n"
                    ),
                },
            )
        )

        fail_report = asyncio.run(workspace_runtime.verify_workspace(mission))
        self.assertFalse(fail_report["passed"])
        self.assertIn("python_tests", fail_report["checks_run"])

        out_patch = asyncio.run(
            workspace_runtime.execute_workspace_tool(
                mission,
                task,
                "workspace_patch_file",
                {
                    "path": "calc.py",
                    "target_block": "    return a - b",
                    "replacement_block": "    return a + b",
                },
            )
        )
        self.assertIn("OK: patch applicata", out_patch)

        read_lines = asyncio.run(
            workspace_runtime.execute_workspace_tool(
                mission,
                task,
                "workspace_read_file",
                {"path": "calc.py", "start_line": 1, "end_line": 5},
            )
        )
        self.assertIn("return a + b", read_lines)

        search_out = asyncio.run(
            workspace_runtime.execute_workspace_tool(
                mission,
                task,
                "workspace_search",
                {"query": "def add"},
            )
        )
        self.assertIn("calc.py:1", search_out)

        pass_report = asyncio.run(workspace_runtime.verify_workspace(mission))
        self.assertTrue(pass_report["passed"])
        self.assertEqual(pass_report["exit_code"], 0)

    def test_dynamic_dag_replan_on_directive(self) -> None:
        task = Task(id="t1", phase_id="p1", title="Init", description="Init", status=TaskStatus.DONE)
        phase = Phase(id="p1", title="Fase 1", description="Init", tasks=[task], status="done")
        mission = Mission(
            id="msn-replan-01",
            title="Portale Web",
            goal="Costruisci portale",
            domain="software",
            phases=[phase],
            status=MissionStatus.DONE,
            progress=100,
        )
        self.store.save(mission)

        mock_replan_llm = {
            "phase_title": "Modulo Pagamenti Stripe",
            "phase_description": "Integrazione checkout",
            "tasks": [
                {
                    "title": "Servizio Checkout",
                    "description": "Crea endpoint pagamento",
                    "specialist_role": "Backend Architect",
                    "criteria": [{"description": "Test pagamenti superati", "target": "100%"}],
                }
            ],
        }

        with mock.patch("features.autonomous_worker.presentation.handlers.mission_store", self.store), \
             mock.patch("features.autonomous_worker.presentation.handlers.notifier.push_mission"), \
             mock.patch("features.autonomous_worker.presentation.handlers.sync_legacy_projects"), \
             mock.patch("features.autonomous_worker.infrastructure.llm_runtime.runtime_manager.generate", return_value=mock_replan_llm):
            updated = asyncio.run(
                apply_mission_directive(
                    "msn-replan-01",
                    {"directive": "Aggiungi ora il modulo pagamenti con test automatici"},
                )
            )
            self.assertEqual(updated["status"], "running")
            self.assertEqual(len(updated["phases"]), 2)
            self.assertEqual(updated["phases"][1]["title"], "Modulo Pagamenti Stripe")
            self.assertLess(updated["progress"], 100)


if __name__ == "__main__":
    unittest.main()
