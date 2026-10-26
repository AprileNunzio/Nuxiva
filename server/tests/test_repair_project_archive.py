import tempfile
import unittest
from pathlib import Path

from server.features.repair_workbench.project_archive import ProjectArchive
from server.features.repair_workbench.session_models import WorkbenchSession


class ProjectArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.now = 100.0
        self.archive = ProjectArchive(self.temp.name, clock=lambda: self.now)
        self.session = WorkbenchSession(session_id="session1", owner_id="owner1",
                                        project_id="project1", created_at=1, updated_at=1)

    def tearDown(self):
        self.temp.cleanup()

    def test_resume_retains_project_data_after_process_restart(self):
        self.session.aliases["C1"] = "Condensatore ingresso"
        self.archive.save_session(self.session, "Riparazione amplificatore")
        reopened = ProjectArchive(self.temp.name).latest_session("owner1", "project1")
        self.assertEqual(reopened.aliases, self.session.aliases)
        self.assertIsNone(self.archive.latest_session("other_owner", "project1"))
        directory = Path(self.temp.name) / "owner1/project1/repair"
        self.assertEqual({p.name for p in directory.iterdir() if p.is_dir()},
                         {"images", "sessions", "schematics", "tasks", "sources", "logs"})
        for file in directory.rglob("*.enc"):
            self.assertNotIn(b"Condensatore", file.read_bytes())

    def test_multiple_open_projects_and_explicit_close(self):
        self.archive.save_session(self.session)
        self.session.project_id = "project2"
        self.session.session_id = "session2"
        self.now = 200
        self.archive.save_session(self.session)
        self.assertEqual([p["project_id"] for p in self.archive.list_projects("owner1")],
                         ["project2", "project1"])
        self.archive.set_status("owner1", "project1", "COMPLETED")
        self.assertEqual(len(self.archive.list_projects("owner1")), 1)
        self.assertEqual(len(self.archive.list_projects("owner1", include_closed=True)), 2)
        self.assertIsNotNone(self.archive.latest_session("owner1", "project1"))

    def test_snapshots_are_deduplicated_throttled_and_bounded(self):
        self.archive.save_session(self.session)
        frame = b"\xff\xd8\xff" + b"example"
        first = self.archive.save_snapshot(self.session, frame)
        self.assertIsNotNone(first)
        self.assertIsNone(self.archive.save_snapshot(self.session, frame))
        self.assertIsNone(self.archive.save_snapshot(self.session, frame + b"2"))
        for index in range(70):
            self.now += 31
            self.archive.save_snapshot(self.session, frame + str(index).encode())
        directory = Path(self.temp.name) / "owner1/project1/repair/images"
        self.assertEqual(len(list(directory.iterdir())), 60)
        self.assertNotIn(frame, (directory / Path(first["file"]).name).read_bytes())

    def test_unchanged_evidence_is_not_logged_repeatedly(self):
        self.archive.save_session(self.session)
        self.archive.save_session(self.session)
        self.assertEqual(self.archive.list_projects("owner1")[0]["event_count"], 1)
        self.session.dossier.summary = "Misura da verificare"
        self.archive.save_session(self.session)
        self.assertEqual(self.archive.list_projects("owner1")[0]["event_count"], 2)

    def test_rejects_traversal_and_snapshot_non_images(self):
        for identifier in ("..", "../escape", "a/b", "a\\b"):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                self.archive.latest_session(identifier, "project1")
        with self.assertRaises(ValueError):
            self.archive.save_snapshot(self.session, b"not an image")

    def test_tampered_manifest_is_not_trusted(self):
        self.archive.save_session(self.session)
        directory = Path(self.temp.name) / "owner1/project1/repair"
        manifest = self.archive._read(directory / "manifest.enc")
        manifest["owner_id"] = "someone_else"
        import json
        self.archive._write(directory / "manifest.enc", json.dumps(manifest).encode())
        with self.assertRaises(ValueError):
            self.archive.latest_session("owner1", "project1")

    def test_late_old_session_does_not_replace_latest_dossier(self):
        self.archive.save_session(self.session)
        newer = self.session.model_copy(deep=True)
        newer.session_id = "session2"
        newer.created_at = 200
        newer.dossier.summary = "Nuova sessione"
        self.archive.save_session(newer)
        self.session.dossier.summary = "Risposta tardiva"
        self.now = 300
        self.archive.save_session(self.session)
        latest = self.archive.latest_session("owner1", "project1")
        self.assertEqual(latest.session_id, "session2")
        self.assertEqual(latest.dossier.summary, "Nuova sessione")

    def test_closed_project_cannot_be_modified_or_revived_by_cached_session(self):
        self.archive.save_session(self.session)
        self.archive.set_status("owner1", "project1", "COMPLETED")
        with self.assertRaises(ValueError):
            self.archive.save_session(self.session, status="ACTIVE")
        with self.assertRaises(ValueError):
            self.archive.save_snapshot(self.session, b"\xff\xd8\xffimage")
        with self.assertRaises(ValueError):
            self.archive.set_status("owner1", "project1", "ACTIVE")
        self.assertEqual(self.archive.list_projects("owner1"), [])
        self.assertIsNotNone(self.archive.latest_session("owner1", "project1"))

    def test_one_corrupt_project_does_not_hide_other_projects(self):
        self.archive.save_session(self.session)
        second = self.session.model_copy(deep=True)
        second.project_id = "project2"
        self.archive.save_session(second)
        path = Path(self.temp.name) / "owner1/project1/repair/manifest.enc"
        path.write_bytes(b"corrupted")
        self.assertEqual([p["project_id"] for p in self.archive.list_projects("owner1")], ["project2"])

    def test_log_records_changed_sections_and_continues_after_five_thousand_events(self):
        import json
        self.archive.save_session(self.session)
        directory = Path(self.temp.name) / "owner1/project1/repair"
        manifest = self.archive._read(directory / "manifest.enc")
        manifest["event_count"] = 5000
        self.archive._write(directory / "manifest.enc", json.dumps(manifest).encode())
        self.session.dossier.summary = "Nuova misura"
        self.archive.save_session(self.session)
        event = self.archive._read(directory / "logs/005001.enc")
        self.assertEqual(set(event["evidence"]), {"dossier"})


if __name__ == "__main__":
    unittest.main()
