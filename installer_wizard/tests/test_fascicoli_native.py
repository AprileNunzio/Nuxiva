import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agenti.team.fascicoli import formato, oscura
from agenti.team.fascicoli.archivio import PyStore

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "RustDossierStore")
NOW = 1_794_499_586_000
KEY = bytes(range(32))
NASTY = ["", "  testo  ", "a\x00b\x1fc\x7f", "<!-- s:goal -->\n## finto", "riga\r\nnuova", " separatore\u0085",
         "---\nschema: x", "€ ünïcödé 😀", "\t\tindentato\n\n\n", "x" * 30000, "## titolo\n- [x] fatto"]
SECRETS = ["password: hunter2", "PASSWORD = 'segreta'", "token=abc.def;resto", "Authorization: Bearer abcdefghijklmnop",
           "sk-abcdefghijklmnopqrstuvwx", "ghp_abcdefghijklmnopqrstuvwxyz", "AKIAABCDEFGHIJKLMNOP", "xoxb-1234567890-abc",
           "AIza" + "a" * 35, "eyJabcdefghij.eyJabcdefghij.abcdefghijkl", "IBAN IT60 X054 2811 1010 0000 0123 456",
           "carta 4111-1111-1111-1111", "ordine 1234567890123", "cf rssmra80a01h501u", "chiave: 1234 e pin=0000",
           "-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----", "parola d'ordine: pippo", "nulla da nascondere"]


def doc(kind: str, body: str = "testo", extra: list | None = None) -> dict:
    return {"front": [["schema", formato.SCHEMA], ["file", kind], ["operazione", "20261112-160626-a3f9c2"], ["livello", "standard"],
                      ["autore", "ceo"], ["creato", "2026-11-12T16:06:26Z"]] + (extra or []),
            "title": "Titolo", "sections": [{"anchor": a, "heading": f"H {a}", "body": body} for a in formato.SECTIONS[kind]]}


@unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
class FormatParityTest(unittest.TestCase):
    def test_render_parse_validate_match(self):
        for kind in formato.SECTIONS:
            for text in NASTY:
                with self.subTest(kind=kind, text=text[:20]):
                    d = doc(kind, text, [["nota", text[:600]], ["Bad", "x"]])
                    rendered = nuxiva_native.dossier_render(json.dumps(d))
                    self.assertEqual(rendered, formato.render(d))
                    self.assertEqual(json.loads(nuxiva_native.dossier_parse(rendered)), formato.parse(rendered))
                    self.assertEqual(json.loads(nuxiva_native.dossier_validate(json.dumps(d), kind)),
                                     formato.validate(formato.sanitize(d), kind))
        broken = doc("piano")
        broken["sections"] = broken["sections"][1:] + [broken["sections"][1]]
        broken["front"] = broken["front"][2:] + [["livello", "boh"]]
        self.assertEqual(json.loads(nuxiva_native.dossier_validate(json.dumps(broken), "esito")),
                         formato.validate(formato.sanitize(broken), "esito"))

    def test_parse_errors_match(self):
        for text in ["", "---", "---\n---\n\n# t\nfuori", "---\nk v\n---\n\n# t\n", "---\nK: v\n---\n\n# t\n",
                     "---\n---\n\n# t\n<!-- s:goal -->\nniente", "---\n---\n\n# t\n<!-- s:goal -->"]:
            with self.subTest(text=text):
                try:
                    py = formato.parse(text)
                except formato.Problem as exc:
                    py = exc.as_dict()
                try:
                    rs = json.loads(nuxiva_native.dossier_parse(text))
                except ValueError as exc:
                    rs = json.loads(str(exc))[0]
                self.assertEqual(rs, py)

    def test_redaction_matches(self):
        keep, whole, card = nuxiva_native.dossier_patterns()
        self.assertEqual((tuple(keep), tuple(whole), card), (oscura.KEEP_PREFIX, oscura.WHOLE, oscura.CARD))
        for text in SECRETS + NASTY:
            with self.subTest(text=text[:30]):
                self.assertEqual(nuxiva_native.dossier_redact(text), oscura.redact(text))
        self.assertNotIn("hunter2", oscura.redact(SECRETS[0]))
        self.assertIn("1234567890123", oscura.redact(SECRETS[12]))

    def test_step_names_match(self):
        for n, slug in [(1, "Cerca email"), (0, "x"), (100, "x"), (5, "---"), (9, "Ünïcode è bello"), (12, "a" * 80)]:
            self.assertEqual(nuxiva_native.dossier_step_file(n, slug), formato.step_file(n, slug))


@unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
class StoreParityTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.rust = nuxiva_native.RustDossierStore(str(self.root), KEY)
        self.py = PyStore(str(self.root), KEY)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _fill(self, writer, level="standard"):
        rel = writer.open(level, NOW)
        for kind in formato.LEVELS[level]:
            name = formato.FIXED.get(kind) or "passi/01-cerca.md"
            d = doc(kind, "password: hunter2 e testo")
            writer.write(rel, name, d if isinstance(writer, PyStore) else json.dumps(d), NOW)
        return rel

    def test_each_engine_verifies_the_other(self):
        for writer, reader in ((self.py, self.rust), (self.rust, self.py)):
            rel = self._fill(writer, "progetto")
            rs = self.rust.verify(rel)
            report = json.loads(rs) if isinstance(rs, str) else rs
            self.assertEqual(report, self.py.verify(rel))
            self.assertTrue(report["ok"] and report["complete"], report)
            text = (self.root / rel / "00-richiesta.md").read_text(encoding="utf-8")
            self.assertNotIn("hunter2", text)
            self.assertEqual(json.loads(self.rust.read(rel, "02-piano.md")), self.py.read(rel, "02-piano.md"))

    def test_tampering_and_pruning_agree(self):
        rel = self._fill(self.py)
        path = self.root / rel / "01-contesto.md"
        path.write_text(path.read_text(encoding="utf-8") + "x", encoding="utf-8")
        self.assertEqual(json.loads(self.rust.verify(rel)), self.py.verify(rel))
        self.assertFalse(self.py.verify(rel)["ok"])
        rel2 = self._fill(self.rust)
        later = NOW + 40 * 86_400_000
        self.assertEqual(self.rust.expired(later, 30, 50), self.py.expired(later, 30, 50))
        self.assertEqual(self.py.prune(rel2, later), 3)
        report = json.loads(self.rust.verify(rel2))
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["files"], ["99-esito.md"])
        other = PyStore(str(self.root), bytes(32))
        self.assertFalse(other.verify(rel2)["ok"])

    def test_recent_and_judge_match(self):
        a = self.py.open("lampo", NOW)
        b = self.rust.open("lampo", NOW + 86_400_000)
        c = self.py.open("lampo", NOW + 86_400_000 + 5000)
        self.assertEqual(self.rust.recent(10), self.py.recent(10))
        self.assertEqual(self.py.recent(10), [c, b, a])
        self.assertEqual(self.rust.recent(1), self.py.recent(1))

    def test_judge_matches(self):
        from agenti.team.fascicoli import giudizio
        full = ["00-richiesta.md", "01-contesto.md", "02-piano.md", "99-esito.md"]
        for level in ("standard", "progetto", "boh"):
            for files in (full, full[:2], []):
                for ok in (True, False):
                    for failed in (0, 1):
                        for status in ("completed", "failed", "unverified", ""):
                            for verified in (True, False):
                                for empty in (True, False):
                                    report = {"ok": ok, "level": level, "complete": False, "files": files, "problems": []}
                                    facts = {"steps_total": 2, "steps_failed": failed, "outcome_status": status,
                                             "outcome_verified": verified, "answer_empty": empty}
                                    self.assertEqual(json.loads(nuxiva_native.dossier_judge(json.dumps(report), json.dumps(facts))),
                                                     giudizio.judge(report, facts))

    def test_native_refuses_bad_input(self):
        with self.assertRaises(ValueError):
            nuxiva_native.RustDossierStore(str(self.root), b"short")
        rel = self.rust.open("lampo", NOW)
        with self.assertRaises(ValueError):
            self.rust.write("../../x/20261112-160626-a3f9c2", "99-esito.md", json.dumps(doc("esito")), NOW)
        with self.assertRaises(ValueError):
            self.rust.write(rel, "99-esito.md", json.dumps(doc("piano")), NOW)
        with self.assertRaises(ValueError):
            self.rust.write(rel, "passi/01-x.md", json.dumps(doc("passo", "y" * 70000)), NOW)
        with self.assertRaises(Exception):
            self.py.write(rel, "passi/01-x.md", doc("passo", "y" * 70000), NOW)
        with self.assertRaises(ValueError):
            nuxiva_native.dossier_prompt("{}", "[]", "corto")


if __name__ == "__main__":
    unittest.main()
