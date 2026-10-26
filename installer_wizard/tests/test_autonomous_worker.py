import asyncio
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.autonomous_worker.application.collab_bus import collab_bus
from features.autonomous_worker.application.deliberator import deliberator
from features.autonomous_worker.application.execution_loop import execution_loop
from features.autonomous_worker.application.specialist_forge import forge
from features.autonomous_worker.commands import answer as commands_answer
from features.autonomous_worker.domain.exceptions import MissionNotFoundError, MissionValidationError
from features.autonomous_worker.domain.models import (
    AcceptanceCriteria,
    Mission,
    MissionStatus,
    Phase,
    Task,
    TaskStatus,
)
from features.autonomous_worker.domain.sanitizer import resolve_safe_path, sanitize_text, validate_identifier
from features.autonomous_worker.infrastructure.artifact_vault import vault
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


if __name__ == "__main__":
    unittest.main()
