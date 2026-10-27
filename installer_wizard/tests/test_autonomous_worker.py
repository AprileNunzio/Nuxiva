import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.autonomous_worker.application.agentic_runner import agentic_runner
from features.autonomous_worker.application.code_intel import code_intel
from features.autonomous_worker.application.sandbox_validator import sandbox_validator
from features.autonomous_worker.application.tool_catalog import tool_catalog
from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.deliberator import deliberator
from features.autonomous_worker.application.execution_loop import execution_loop
from features.autonomous_worker.application.memory_compressor import memory_compressor
from features.autonomous_worker.application.specialist_forge import forge
from features.autonomous_worker.commands import answer as commands_answer
from features.autonomous_worker.domain.exceptions import MissionNotFoundError, MissionValidationError
from features.autonomous_worker.domain.models import (
    AcceptanceCriteria,
    CollabMessage,
    Mission,
    MissionStatus,
    Phase,
    Task,
    TaskStatus,
)
from features.autonomous_worker.domain.sanitizer import resolve_safe_path, sanitize_text, validate_identifier
from features.autonomous_worker.infrastructure.artifact_vault import vault
from features.autonomous_worker.infrastructure.llm_runtime import runtime_manager
from features.autonomous_worker.infrastructure.store import MissionStore
from features.autonomous_worker.presentation.desk_notifier import notifier


class AutonomousWorkerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp()).resolve()
        self.store = MissionStore(data_dir=self.temp_dir / "store")
        self.vault_dir = self.temp_dir / "vault"
        vault.root = self.vault_dir
        vault.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitizer_and_zero_trust_paths(self):
        dirty = "<script>alert('xss')</script>\x00hello\r\n"
        cleaned = sanitize_text(dirty)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("\x00", cleaned)
        self.assertIn("hello", cleaned)

        valid_id = validate_identifier("msn-123_abc.test")
        self.assertEqual(valid_id, "msn-123_abc.test")

        with self.assertRaises(MissionValidationError):
            validate_identifier("../evil_id")

        base = self.temp_dir / "safe_base"
        base.mkdir(parents=True, exist_ok=True)
        safe_target = resolve_safe_path(base, "sub/file.txt")
        self.assertTrue(str(safe_target).startswith(str(base)))

        with self.assertRaises(MissionValidationError):
            resolve_safe_path(base, "../../etc/passwd")

    def test_store_persistence_and_encryption(self):
        mission = Mission(
            id="msn-test-01",
            title="E-Commerce Enterprise",
            goal="Creami un sito ecommerce informatica",
            domain="software",
            status=MissionStatus.RUNNING,
        )
        saved = self.store.save(mission)
        self.assertEqual(saved.id, "msn-test-01")

        loaded = self.store.get("msn-test-01")
        self.assertEqual(loaded.title, "E-Commerce Enterprise")
        self.assertEqual(loaded.domain, "software")

        self.assertTrue(self.store.sealed_file.exists())
        self.assertTrue(self.store.key_file.exists())
        self.assertTrue(self.store.index_file.exists())

        active = self.store.active()
        self.assertEqual(len(active), 1)

        self.store.remove("msn-test-01")
        with self.assertRaises(MissionNotFoundError):
            self.store.get("msn-test-01")

    def test_specialist_forge_and_team_assembly(self):
        task1 = Task(id="t1", phase_id="p1", title="UI Layout", description="Design system", specialist_role="UI Designer")
        task2 = Task(id="t2", phase_id="p1", title="Security Audit", description="Zero Trust check", specialist_role="Security Lead")
        phase = Phase(id="p1", title="Architecture", description="Initial Phase", tasks=[task1, task2])

        mission = Mission(
            id="msn-forge-01",
            title="Sito E-Commerce",
            goal="Costruisci il portale",
            domain="software",
            phases=[phase],
        )

        team = forge.assemble_team(mission)
        self.assertEqual(len(team), 2)
        roles = {s.mission_role for s in team}
        self.assertIn("UI Designer", roles)
        self.assertIn("Security Lead", roles)
        self.assertTrue(task1.specialist_id.startswith("exp_"))
        self.assertEqual(task1.specialist_role, "UI Designer")

    def test_collab_bus_and_board_posting(self):
        mission = Mission(id="msn-collab", title="Missione Collab", goal="Goal", domain="general")
        with mock.patch("features.autonomous_worker.application.collab_bus.board.post") as mock_post:
            msg = collab_bus.post(
                mission=mission,
                sender_id="sec_lead",
                sender_role="Security Lead",
                content="Protocollo crittografico approvato.",
                kind="approval",
            )
            self.assertEqual(msg.kind, "approval")
            self.assertEqual(len(mission.collab_messages), 1)
            mock_post.assert_called_once()

    def test_artifact_vault_storage_and_integrity(self):
        mission = Mission(id="msn-vault-01", title="Title", goal="Goal", domain="software")
        art = vault.store_file(
            mission=mission,
            relative_path="src/index.ts",
            content="export const app = () => {};",
            generated_by="Frontend Lead",
            title="Entry Point",
        )
        self.assertEqual(art.relative_path, "src/index.ts")
        self.assertTrue(len(art.checksum) > 20)
        self.assertEqual(len(mission.artifacts), 1)

        read_back = vault.read_file("msn-vault-01", "src/index.ts")
        self.assertIn("export const app", read_back)

    def test_deliberation_and_question_handling(self):
        mock_llm_reply = {
            "title": "E-Commerce Enterprise",
            "domain": "software",
            "questions": [
                {
                    "id": "q1",
                    "question": "Preferisci MD3 Express o token CSS interni?",
                    "options": ["MD3 Express", "Token CSS Interni"],
                    "is_multi_select": False,
                    "rationale": "Scelta architettura UI",
                }
            ],
            "phases": [
                {
                    "id": "p1",
                    "title": "Analisi e Requisiti",
                    "description": "Fase iniziale",
                    "tasks": [
                        {
                            "id": "t1",
                            "title": "Definizione Contratti",
                            "description": "Scrittura OpenAPI",
                            "specialist_role": "Backend Architect",
                            "criteria": [{"description": "File openapi.json presente", "target": "100%"}],
                        }
                    ],
                }
            ],
        }

        with mock.patch("features.brain.llm.generate", return_value=mock_llm_reply):
            mission = asyncio.run(
                deliberator.deliberate(goal="Creami un sito ecommerce per prodotti informatici")
            )
            self.assertEqual(mission.domain, "software")
            self.assertEqual(mission.status, MissionStatus.QUESTION)
            self.assertEqual(len(mission.questions), 1)
            self.assertEqual(mission.questions[0].id, "q1")
            self.assertEqual(len(mission.phases), 1)
            self.assertEqual(len(mission.phases[0].tasks), 1)

    def test_execution_loop_tick_and_auto_healing(self):
        task = Task(
            id="t1",
            phase_id="p1",
            title="Architettura Core",
            description="Scrivi schema",
            specialist_role="Core Architect",
            criteria=[AcceptanceCriteria(description="Schema validato")],
        )
        phase = Phase(id="p1", title="Fase 1", description="Desc", tasks=[task])
        mission = Mission(
            id="msn-loop-01",
            title="Mission Loop",
            goal="Goal",
            domain="software",
            phases=[phase],
            status=MissionStatus.RUNNING,
        )

        with mock.patch("features.autonomous_worker.application.execution_loop.mission_store", self.store), \
             mock.patch("features.autonomous_worker.application.execution_loop.notifier.push_mission") as mock_push, \
             mock.patch("features.brain.llm.generate") as mock_llm:

            mock_llm.side_effect = [
                {"result": "Schema redatto", "collab_note": "Interfaccia pronta"},
                {"approved": False, "feedback": "Mancano gli standard Zero-Trust"},
                {"result": "Schema corretto con Zero-Trust", "collab_note": "Correzione pronta"},
                {"approved": True, "feedback": ""},
                {"complete": True},
            ]

            asyncio.run(execution_loop.tick_mission(mission))
            self.assertEqual(task.status, TaskStatus.PENDING)
            self.assertEqual(task.round, 2)
            self.assertIn("Zero-Trust", task.feedback)

            asyncio.run(execution_loop.tick_mission(mission))
            self.assertEqual(task.status, TaskStatus.DONE)
            self.assertTrue(task.criteria[0].verified)

            asyncio.run(execution_loop.tick_mission(mission))
            self.assertEqual(mission.status, MissionStatus.DONE)
            mock_push.assert_called()

    def test_desk_notifier_payload(self):
        mission = Mission(
            id="msn-desk-01",
            title="Titolo Missione",
            goal="Goal",
            domain="finance",
            status=MissionStatus.RUNNING,
        )
        with mock.patch("features.autonomous_worker.presentation.desk_notifier.desk.show") as mock_show:
            notifier.push_mission(mission)
            mock_show.assert_called_once()
            args = mock_show.call_args[0]
            self.assertEqual(args[0], "mission_tracker")
            self.assertEqual(args[1]["id"], "msn-desk-01")
            self.assertEqual(args[1]["domain"], "finance")

    def test_commands_answer_integration(self):
        mock_delib = Mission(
            id="msn-cmd-01",
            title="Analisi di Mercato",
            goal="Analizza il mercato delle rinnovabili",
            domain="research",
            status=MissionStatus.RUNNING,
        )
        with mock.patch("features.autonomous_worker.commands.deliberator.deliberate", return_value=mock_delib), \
             mock.patch("features.autonomous_worker.commands.mission_store.save"), \
             mock.patch("features.autonomous_worker.commands.notifier.push_mission"):

            speech, ui = asyncio.run(
                commands_answer("analizza e pianifica la strategia per le rinnovabili")
            )
            self.assertIn("CEO ha avviato la missione autonoma", speech)
            self.assertEqual(ui["mode"], "focus")
            self.assertEqual(ui["widget"], "mission_tracker")

    def test_runtime_manager_configuration_and_health(self):
        cfg = runtime_manager.get_config()
        self.assertIn("mode", cfg)
        updated = runtime_manager.update_config({"mode": "cloud", "token_rate_limit_per_min": 80000})
        self.assertEqual(updated["mode"], "cloud")
        self.assertEqual(updated["token_rate_limit_per_min"], 80000)

        health = asyncio.run(runtime_manager.check_health())
        self.assertTrue(health["healthy"])
        self.assertEqual(health["mode"], "cloud")

    def test_episodic_memory_and_automatic_compression(self):
        mission = Mission(
            id="msn-mem-01",
            title="Sito E-Commerce",
            goal="Costruisci il portale",
            domain="software",
            status=MissionStatus.RUNNING,
        )
        self.assertFalse(memory_compressor.should_compress(mission))

        for i in range(20):
            mission.collab_messages.append(
                CollabMessage(
                    id=f"msg_{i}",
                    sender_id=f"agent_{i % 3}",
                    sender_role="Developer",
                    target_id="all",
                    channel="collab",
                    content=f"Dettaglio sviluppo elemento #{i}",
                    kind="chat",
                )
            )

        self.assertTrue(memory_compressor.should_compress(mission))

        mock_payload = {
            "summary": "Implementato nucleo architettura con autenticazione",
            "lessons_learned": ["Evitare dipendenze circolari tra moduli", "Usare timeout espliciti su HTTP"],
            "key_decisions": ["Adottata Clean Architecture", "Separazione Net e DB"],
        }
        with mock.patch("features.autonomous_worker.infrastructure.llm_runtime.runtime_manager.generate", return_value=mock_payload):
            compressed = asyncio.run(memory_compressor.compress(mission))
            self.assertTrue(compressed)
            self.assertEqual(mission.memory.compression_count, 1)
            self.assertEqual(mission.memory.summary, "Implementato nucleo architettura con autenticazione")
            self.assertIn("Evitare dipendenze circolari tra moduli", mission.memory.lessons_learned)
            self.assertIn("Adottata Clean Architecture", mission.memory.key_decisions)
            self.assertEqual(len(mission.collab_messages), 7)
            self.assertEqual(mission.collab_messages[-1].sender_id, "memory_synthesizer")

    def test_agent_inference_profiles_and_routing(self):
        profile = {
            "agent_id": "qa_checker",
            "label": "Controllo Qualità",
            "provider": "ollama",
            "endpoint": "http://127.0.0.1:11434",
            "model": "gemma4",
            "temperature": 0.1,
            "timeout_seconds": 30,
        }
        saved = runtime_manager.set_agent_profile(profile)
        self.assertEqual(saved["agent_id"], "qa_checker")
        self.assertEqual(saved["model"], "gemma4")

        found = runtime_manager.get_agent_profile("qa_checker")
        self.assertIsNotNone(found)
        self.assertEqual(found["provider"], "ollama")

        all_profiles = runtime_manager.list_agent_profiles()
        self.assertTrue(any(p["agent_id"] == "qa_checker" for p in all_profiles))

        resolved = runtime_manager._resolve_profile("qa_checker", "Ispettore")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.model, "gemma4")

        resolved_by_role = runtime_manager._resolve_profile(None, "Controllo Qualità")
        self.assertIsNotNone(resolved_by_role)
        self.assertEqual(resolved_by_role.agent_id, "qa_checker")

        with mock.patch.object(runtime_manager, "_call_ollama", return_value={"result": "OK"}) as mock_call:
            res = asyncio.run(
                runtime_manager.generate(
                    "Test prompt",
                    agent_id="qa_checker",
                )
            )
            self.assertEqual(res, {"result": "OK"})
            mock_call.assert_called_once()

        deleted = runtime_manager.delete_agent_profile("qa_checker")
        self.assertTrue(deleted)
        self.assertIsNone(runtime_manager.get_agent_profile("qa_checker"))

    def test_lessons_learned_injected_in_task_prompt(self):
        mission = Mission(
            id="msn-prompt-01",
            title="Missione Sicurezza",
            goal="Verificare conformità OWASP",
            domain="security",
            status=MissionStatus.RUNNING,
        )
        mission.memory.lessons_learned = ["Non usare eval()", "Validare sempre gli identifier"]
        mission.memory.key_decisions = ["Zero-Trust obbligatorio"]

        task = Task(
            id="t_sec",
            phase_id="p1",
            title="Analisi Input",
            description="Controllo sanitizzazione",
            specialist_id="sec_auditor",
            specialist_role="Security Auditor",
        )
        mission.phases.append(Phase(id="p1", title="Audit", description="Audit", tasks=[task]))

        captured_prompt = {}

        async def fake_generate(prompt, **kwargs):
            captured_prompt["prompt"] = prompt
            return {"result": "Sanitizzazione verificata", "artifacts": []}

        with mock.patch("features.autonomous_worker.infrastructure.llm_runtime.runtime_manager.generate", side_effect=fake_generate):
            asyncio.run(execution_loop._run_task(mission, task))
            self.assertIn("Non usare eval()", captured_prompt["prompt"])
            self.assertIn("Zero-Trust obbligatorio", captured_prompt["prompt"])
            self.assertEqual(task.status, TaskStatus.REVIEW)

    def test_tool_catalog_scan_and_categorize(self):
        catalog = tool_catalog.scan_all_tools(force_refresh=True)
        self.assertGreater(catalog["total_tools"], 50)
        self.assertIn("system_os", catalog["categories"])
        self.assertIn("home_automation", catalog["categories"])
        self.assertIn("media_tv", catalog["categories"])

    def test_tool_catalog_task_ranking(self):
        task_ha = Task(
            id="t_ha",
            phase_id="p1",
            title="Accendi luci salotto",
            description="Controllo entità home assistant luce",
            specialist_id="iot_dev",
            specialist_role="IoT Specialist",
        )
        ranked = tool_catalog.get_relevant_tools_for_task(task_ha, limit=10)
        names = [t["name"] for t in ranked]
        self.assertTrue(any("ha_" in n for n in names) or "read_file" in names)

    def test_tool_catalog_study_and_forge(self):
        spec = {
            "name": "audit_system_health",
            "description": "Controlla lo stato del sistema e scrive il report",
            "params": {"target_dir": "cartella di destinazione"},
            "steps": [{"tool": "list_dir", "args": {"path": "{{target_dir}}"}}]
        }
        res = asyncio.run(tool_catalog.study_and_forge_tool(spec))
        self.assertTrue(res["success"])
        self.assertEqual(res["name"], "audit_system_health")

    def test_agentic_runner_multi_step_tool_call(self):
        mission = Mission(id="m_ag", title="Ag Mission", goal="Test tool", domain="dev")
        task = Task(id="t_ag", phase_id="p1", title="Test Task", description="Testing", specialist_id="sp", specialist_role="Dev")
        calls = [
            {"tool": "list_dir", "args": {"path": "."}},
            {"result": "Directory letta con successo", "artifacts": []}
        ]

        async def mock_gen(*args, **kwargs):
            return calls.pop(0)

        with mock.patch("features.autonomous_worker.infrastructure.llm_runtime.runtime_manager.generate", side_effect=mock_gen):
            res = asyncio.run(agentic_runner.execute_task_with_tools(mission, task, "Esegui"))
            self.assertEqual(res.get("result"), "Directory letta con successo")

    def test_code_intel_atomic_patch_and_reasoning(self):
        mission = Mission(id="msn-patch-01", title="Patch Test", goal="Verifica AST e Patch", domain="software")
        art1 = vault.store_file(
            mission=mission,
            relative_path="src/service.py",
            content="class OrderService:\n    def total(self):\n        return 10\n",
            generated_by="Backend Lead",
        )
        self.assertIn("class OrderService (total)", art1.symbols)
        self.assertEqual(art1.line_count, 3)

        art2 = vault.apply_atomic_patch(
            mission=mission,
            relative_path="src/service.py",
            target_block="        return 10",
            replacement_block="        return 42",
            generated_by="Backend Lead",
            expected_checksum=art1.checksum,
        )
        self.assertIn("-        return 10", art2.diff)
        self.assertIn("+        return 42", art2.diff)

        repo_map = code_intel.export_repo_map_data(mission)
        self.assertEqual(repo_map["total_files"], 1)
        self.assertEqual(repo_map["total_symbols"], 1)

        valid, err = sandbox_validator.validate_code("big.py", "\n".join(["x = 1"] * 505))
        self.assertFalse(valid)
        self.assertIn("500", err)


if __name__ == "__main__":
    unittest.main()
