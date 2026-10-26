import asyncio
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from features.devstudio import builder, plan as plans, starters, tools, workspace


def run(coro):
    return asyncio.run(coro)


class BuilderCase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for target, name, value in ((workspace, "ROOT", root / "progetti"), (plans, "PLAN_DIR", root / "piani")):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        run(tools.dev_new("negozio", "php_site"))
        self.replies = []

        async def fake(prompt, **kwargs):
            self.last_prompt = prompt
            return self.replies.pop(0)

        patcher = mock.patch.object(builder, "generate", fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def plan(self, files=None):
        files = files or [{"path": "pages/shop/view.phtml", "purpose": "catalogo"}, {"path": "pages/shop/style.css", "purpose": "stile"}]
        self.replies.append({"stack": "php e js", "files": files})
        return run(tools.dev_plan("negozio", "negozio online con catalogo e carrello"))


class PlanTests(BuilderCase):

    def test_plan_is_saved_and_survives_reload(self):
        self.assertIn("2 file", self.plan())
        status = run(tools.dev_status("negozio"))
        self.assertIn("pending: pages/shop/view.phtml", status)
        self.assertIn("negozio online", status)

    def test_plan_rejects_paths_outside_the_project(self):
        for bad in ("../fuori.php", "a/../../b.php", ""):
            self.assertTrue(self.plan([{"path": bad, "purpose": "x"}]).startswith("ERRORE"), bad)

    def test_plan_requires_a_real_goal_and_an_existing_project(self):
        self.assertTrue(run(tools.dev_plan("negozio", "sito")).startswith("ERRORE"))
        self.assertTrue(run(tools.dev_plan("inesistente", "negozio online completo")).startswith("ERRORE"))

    def test_status_without_plan_explains_what_to_do(self):
        self.assertIn("dev_plan", run(tools.dev_status("negozio")))


class BuildTests(BuilderCase):

    def test_files_are_written_one_at_a_time_and_progress_is_kept(self):
        self.plan()
        self.replies += ["```html\n<main></main>\n```", "main { margin: 0; }\n"]
        out = run(tools.dev_build("negozio", 1))
        self.assertIn("scritto pages/shop/view.phtml", out)
        self.assertIn("1 in attesa", out)
        self.assertEqual(workspace.read(workspace.project_dir("negozio"), "pages/shop/view.phtml").strip(), "<main></main>")
        out = run(tools.dev_build("negozio", 3))
        self.assertIn("0 in attesa", out)
        self.assertIn("pages/shop/view.phtml", self.last_prompt)

    def test_commented_code_is_regenerated_once(self):
        self.plan([{"path": "app.js", "purpose": "avvio"}])
        self.replies += ["// avvio\nconst a = 1;\n", "const a = 1;\n"]
        self.assertIn("scritto app.js", run(tools.dev_build("negozio", 1)))
        self.assertNotIn("//", workspace.read(workspace.project_dir("negozio"), "app.js"))

    def test_oversized_file_is_refused_and_marked_for_review(self):
        self.plan([{"path": "grande.js", "purpose": "tutto"}])
        self.replies += ["x\n" * 600, "x\n" * 600]
        out = run(tools.dev_build("negozio", 1))
        self.assertIn("NON scritto grande.js", out)
        self.assertIn("1 da rivedere", out)
        self.assertIn("failed: grande.js", run(tools.dev_status("negozio")))

    def test_unreachable_model_stops_without_losing_the_plan(self):
        self.plan()
        from features.brain.llm import BrainUnavailable

        async def down(prompt, **kwargs):
            raise BrainUnavailable("offline")

        with mock.patch.object(builder, "generate", down):
            self.assertTrue(run(tools.dev_build("negozio", 1)).startswith("ERRORE"))
        self.assertIn("2 in attesa", run(tools.dev_status("negozio")))


class GrantTests(unittest.TestCase):

    def test_existing_programming_experts_receive_the_build_tools(self):
        from features.experts import service, store as store_module
        from features.experts.model import build
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            for name, file in (("PROFILES", "e.json"), ("HISTORY", "h.sealed"), ("HISTORY_KEY", "h.key"), ("SEEDED", "s.json")):
                patcher = mock.patch.object(store_module, name, base / file)
                patcher.start()
                self.addCleanup(patcher.stop)
            fresh = store_module.ExpertStore()
            swap = mock.patch.object(service, "experts", fresh)
            swap.start()
            self.addCleanup(swap.stop)
            known = {"dev_new", "dev_write", "dev_plan", "dev_build", "dev_status", "now"}
            with mock.patch.object(service, "known_tools", return_value=known):
                fresh.put(build({"id": "vecchio", "role": "Programmatore", "specialty": "codice", "tools": ["dev_new", "dev_write"]}, known), create=True)
                fresh.put(build({"id": "altro", "role": "Cuoco", "specialty": "cucina", "tools": ["now"]}, known), create=True)
                self.assertEqual(service.grant_build_tools(), 1)
                self.assertEqual(service.grant_build_tools(), 0)
            self.assertIn("dev_build", fresh.get("vecchio").tools)
            self.assertNotIn("dev_build", fresh.get("altro").tools)


@unittest.skipUnless(shutil.which("php"), "php assente")
class PhpStarterTests(unittest.TestCase):

    def test_every_php_file_of_the_starter_is_valid(self):
        with tempfile.TemporaryDirectory() as root:
            for relative, content in starters.scaffold("php_site", "demo").items():
                target = Path(root) / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                if relative.endswith((".php", ".phtml")):
                    check = subprocess.run(["php", "-l", str(target)], capture_output=True, text=True)
                    self.assertEqual(check.returncode, 0, f"{relative}: {check.stdout}{check.stderr}")

    def test_starter_has_no_comments_and_stays_small(self):
        for relative, content in starters.scaffold("php_site", "demo").items():
            self.assertLess(len(content.splitlines()), 500, relative)
            self.assertFalse(builder._commented(relative, content), relative)


if __name__ == "__main__":
    unittest.main()
