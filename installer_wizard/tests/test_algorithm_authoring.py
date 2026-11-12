import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.skills import api, authoring, catalog
from features.skills import library as lib

CODE = (
    "import re\n\n\n"
    "def run(text):\n"
    "    m = re.search(r'(\\d+)\\s*piu\\s*(\\d+)', text)\n"
    "    if not m:\n"
    "        return {'ok': False, 'error': 'numeri mancanti'}\n"
    "    total = int(m.group(1)) + int(m.group(2))\n"
    "    return {'ok': True, 'result': total, 'speech': f'Fa {total}'}\n"
)
SPEC = {"name": "Somma di prova", "category": "matematica", "description": "Somma due numeri",
        "patterns": [r"\d+\s*piu\s*\d+"], "examples": ["3 piu 4"], "code": CODE}


class AuthoringTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "user").mkdir()
        for name, value in (("USER_DIR", root / "user"), ("SYSTEM_DIR", root / "system"), ("STATS_FILE", root / "stats.json")):
            patcher = mock.patch.object(lib, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.library = lib.Library()
        patcher = mock.patch.object(authoring, "library", self.library)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addAsyncCleanup(self.stop_worker)

    async def stop_worker(self):
        proc = self.library.worker.proc
        if proc and proc.returncode is None:
            proc.kill()
            await proc.wait()

    async def test_create_tests_the_code_and_installs_a_user_algorithm(self):
        key = await authoring.create(SPEC, "3 piu 4")
        self.assertEqual(key, "matematica/somma_di_prova")
        item = self.library.listing()["skills"][0]
        self.assertEqual(item["source"], "user")
        answer = await self.library.try_answer("quanto fa 20 piu 22")
        self.assertEqual(answer["speech"], "Fa 42")

    async def test_dangerous_or_broken_input_is_refused(self):
        for patch in ({"code": "import os\ndef run(text):\n    return {}"}, {"code": "def run(text:\n"}, {"code": "x = 1"},
                      {"patterns": []}, {"patterns": ["("]}, {"name": ""}, {"patterns": [r"\d+ ciao"]}):
            with self.assertRaises(authoring.AuthoringError, msg=str(patch)):
                await authoring.create({**SPEC, **patch}, "3 piu 4")
        self.assertEqual(self.library.listing()["skills"], [])

    async def test_a_code_that_fails_its_probe_is_not_installed(self):
        bad = CODE.replace("'ok': True", "'ok': False")
        with self.assertRaises(authoring.AuthoringError):
            await authoring.create({**SPEC, "code": bad}, "3 piu 4")
        self.assertEqual(self.library.listing()["skills"], [])

    async def test_replace_code_keeps_the_old_code_when_the_new_one_fails(self):
        key = await authoring.create(SPEC, "3 piu 4")
        await authoring.replace_code(key, CODE.replace("Fa ", "Risultato "))
        self.assertIn("Risultato", self.library.code(key))
        with self.assertRaises(authoring.AuthoringError):
            await authoring.replace_code(key, CODE.replace("'ok': True", "'ok': False"))
        self.assertIn("Risultato", self.library.code(key))
        with self.assertRaises(authoring.AuthoringError):
            await authoring.replace_code(key, "import os\ndef run(text):\n    return {}")
        with self.assertRaises(KeyError):
            await authoring.replace_code("matematica/inesistente", CODE)

    async def test_catalog_lists_skills_tools_and_connectors(self):
        await authoring.create(SPEC, "3 piu 4")
        with mock.patch.object(catalog, "library", self.library):
            result = catalog.scan()
        kinds = {entry["kind"] for entry in result["entries"]}
        self.assertEqual(kinds, {"skill", "tool", "connector"})
        skill = next(e for e in result["entries"] if e["kind"] == "skill")
        self.assertTrue(skill["manageable"] and skill["editable"])
        self.assertTrue(all(not e["manageable"] for e in result["entries"] if e["kind"] != "skill"))
        self.assertEqual(result["counts"]["skill"], 1)

    async def test_generate_refuses_when_creation_is_off(self):
        with mock.patch.object(self.library, "may_generate", return_value=False):
            with self.assertRaises(authoring.AuthoringError):
                await authoring.generate("somma due numeri")


class RoutesTest(unittest.TestCase):
    def test_validation_errors_are_422_and_admin_is_required(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        client = TestClient(app)
        self.assertIn(client.post("/api/skills", json={}).status_code, (401, 403))
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.assertEqual(client.post("/api/skills", json={"name": "x"}).status_code, 422)
        self.assertEqual(client.post("/api/skills/generate", json={"description": ""}).status_code, 422)
        self.assertEqual(client.put("/api/skills/matematica/inesistente/code", json={"code": "def run(t): return {}"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
