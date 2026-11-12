import io
import json
import os
import shutil
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from agenti import __main__ as cli
from agenti import _icon, _layout, _scaffold
from agenti._registry import AgentRegistry, root

SPEC = {
    "id": "medico_prova", "category": "salute", "name": "Medico di prova",
    "description": "Analizza battito e stress", "capabilities": ["Battito"], "nouns": ["battito", "stress"],
}


def unpack(png: bytes) -> bytes:
    body = png[8:]
    data = b""
    while body:
        size = int.from_bytes(body[:4], "big")
        kind, chunk = body[4:8], body[8:8 + size]
        if kind == b"IDAT":
            data += chunk
        body = body[12 + size:]
    return zlib.decompress(data)


class IconTest(unittest.TestCase):
    def test_icon_is_a_decodable_rgba_png(self):
        png = _icon.render("salute", "medico")
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        raw = unpack(png)
        self.assertEqual(len(raw), 64 * (64 * 4 + 1))
        self.assertEqual(raw[1:5], b"\x00\x00\x00\x00")

    def test_icon_depends_on_category_and_id(self):
        self.assertEqual(_icon.render("sport", "calcio"), _icon.render("sport", "calcio"))
        self.assertNotEqual(_icon.render("sport", "calcio"), _icon.render("salute", "calcio"))
        self.assertNotEqual(_icon.render("sport", "calcio"), _icon.render("sport", "tennis"))


class ScaffoldTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, True)
        self.registry = AgentRegistry(lambda: [root(self.base, "system", "categorized")], native=False)

    def test_scaffold_produces_a_complete_valid_agent(self):
        target = _scaffold.create(SPEC, self.base, self.registry)
        self.assertEqual(target, self.base / "salute" / "medico_prova")
        report = _layout.inspect(target)
        self.assertTrue(report["complete"])
        self.assertEqual(report["score"], 100)
        self.assertEqual(self.registry.get("medico_prova").category, "salute")
        self.assertEqual(self.registry.rejected(), [])
        for path in target.rglob("*.py"):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        locale = json.loads((target / "language" / "es.json").read_text(encoding="utf-8"))
        self.assertEqual(locale["meta"]["locale"], "es")
        self.assertEqual([p.name for p in self.base.joinpath("salute").iterdir()], ["medico_prova"])

    def test_duplicates_and_bad_specs_are_refused(self):
        _scaffold.create(SPEC, self.base, self.registry)
        with self.assertRaises(_layout.ScaffoldError) as dup:
            _scaffold.create(SPEC, self.base, self.registry)
        self.assertEqual(dup.exception.issues[0]["code"], "id_duplicate")
        cases = [({"category": "inventata"}, "category_unknown"), ({"id": "Bad Id"}, "id_invalid"),
                 ({"description": "  "}, "description_missing"), ({"name": "x\u0007"}, "control_chars")]
        for change, code in cases:
            with self.subTest(code=code), self.assertRaises(_layout.ScaffoldError) as bad:
                _layout.scaffold({**SPEC, **change})
            self.assertIn(code, [i["code"] for i in bad.exception.issues])

    def test_internal_module_name_in_another_category_is_refused(self):
        (self.base / "sicurezza" / "medico_prova").mkdir(parents=True)
        with self.assertRaises(_layout.ScaffoldError) as bad:
            _scaffold.create(SPEC, self.base, self.registry)
        self.assertEqual(bad.exception.issues[0]["code"], "id_duplicate")

    def test_symlinked_base_is_refused(self):
        link = self.base / "link"
        os.symlink(self.base / "salute", link, target_is_directory=True)
        with self.assertRaises(_layout.ScaffoldError) as bad:
            _scaffold.create(SPEC, link, self.registry)
        self.assertEqual(bad.exception.issues[0]["code"], "path_symlink")

    def test_similar_agents_are_found_before_creating(self):
        _scaffold.create(SPEC, self.base, self.registry)
        twin = {**SPEC, "id": "dottore", "name": "Dottore"}
        self.assertEqual(_scaffold.similar(twin, self.registry)[0][0], "medico_prova")

    def test_inspect_reports_each_missing_part(self):
        folder = self.base / "salute" / "vuoto"
        folder.mkdir(parents=True)
        (folder / "skills.py").write_text("")
        report = _layout.inspect(folder)
        self.assertFalse(report["complete"])
        self.assertNotIn("skills/", report["missing"])
        self.assertIn("algorithms/", report["missing"])
        self.assertEqual(report["score"], 100 // len(_layout.required_parts()))


class CliTest(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_messages_are_complete_in_every_language(self):
        keys = [set(cli._messages(lang)) for lang in cli.SUPPORTED]
        self.assertTrue(all(k == keys[0] for k in keys))

    def test_check_reports_score_for_a_known_agent(self):
        code, out, _ = self.run_cli("--lingua", "en", "verifica", "particles")
        self.assertIn("particles [creativita]", out)
        self.assertIn(code, (0, 1))

    def test_unknown_agent_and_similar_request_are_refused(self):
        self.assertEqual(self.run_cli("verifica", "../etc")[0], 2)
        code, _, err = self.run_cli("--lingua", "it", "nuovo", "--id", "nuvola_particelle", "--categoria", "creativita",
                                    "--nome", "Particelle", "--descrizione", "Scultore di particelle 3D", "--parole", "medusa")
        self.assertEqual(code, 3)
        self.assertIn("particles", err)


if __name__ == "__main__":
    unittest.main()
