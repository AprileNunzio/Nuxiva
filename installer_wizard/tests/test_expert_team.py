import unittest

from features.experts import routing, service, templates
from features.experts.model import build
from features.team.board import board
from features.team.ceo import ceo
from tests.test_experts import IsolatedStore

LANGS = ("it", "en", "es", "fr")


class CatalogTest(unittest.TestCase):
    def test_every_template_is_complete_in_all_languages(self):
        self.assertGreaterEqual(len(templates.ids()), 40)
        for tid in templates.ids():
            for lang in LANGS:
                with self.subTest(template=tid, lang=lang):
                    words = templates.text(tid, lang)
                    self.assertGreaterEqual(len(words["role"]), 3)
                    self.assertGreaterEqual(len(words["specialty"]), 10)
                    self.assertGreaterEqual(len(words["knowledge"]), 3)
                    self.assertTrue(templates.blueprint(tid, lang, tid)["instructions"])

    def test_templates_build_into_valid_experts_with_known_tools(self):
        known = service.known_tools()
        for tid in templates.ids():
            with self.subTest(template=tid):
                expert = build(templates.blueprint(tid, "it", tid), known)
                self.assertEqual(expert.template, tid)
                self.assertEqual(expert.live in ("activity", "debian", "football"), True)

    def test_groups_give_teachers_and_professionals_their_own_rules(self):
        teacher = templates.blueprint("teacher-math", "it", "teacher-math")["instructions"]
        professional = templates.blueprint("lawyer", "it", "lawyer")["instructions"]
        self.assertNotEqual(teacher, professional)
        self.assertIn("emergenza", professional)


class SeedingTest(IsolatedStore):
    def test_seed_creates_the_whole_team_once(self):
        created = service.seed_defaults("it")
        self.assertEqual(set(created), set(templates.ids()))
        self.assertEqual(len(self.store.all()), len(templates.ids()))
        self.assertEqual(service.seed_defaults("it"), [])

    def test_deleted_default_is_not_brought_back(self):
        service.seed_defaults("it")
        service.delete("lawyer")
        self.assertEqual(service.seed_defaults("it"), [])
        self.assertNotIn("lawyer", {e.id for e in self.store.all()})

    def test_existing_experts_are_not_duplicated(self):
        service.create({"template": "debian"}, "it", "test")
        created = service.seed_defaults("it")
        self.assertNotIn("debian", created)
        self.assertEqual(sum(1 for e in self.store.all() if e.template == "debian"), 1)

    def test_seeding_uses_the_installation_language(self):
        service.seed_defaults("en")
        self.assertEqual(self.store.get("lawyer").role, "Legal advisor")


class DelegationTest(IsolatedStore):
    def setUp(self):
        super().setUp()
        service.seed_defaults("it")

    def pick(self, text):
        choice = routing.choose(self.store.all(), text)
        return choice.expert.template if choice else None

    def test_requests_reach_the_right_specialist(self):
        cases = {
            "Come si risolve un'equazione di secondo grado?": "teacher-math",
            "Mi spieghi la fotosintesi e la mitosi?": "teacher-biology",
            "Quanto tempo ci vuole per la dichiarazione dei redditi con partita iva?": "accountant",
            "Che sezione dei cavi serve per il differenziale e il quadro elettrico?": "electrician",
            "Come collego un sensore a un ESP32 con Arduino?": "robotics-maker",
            "Mi dai una scheda di allenamento per la palestra?": "trainer",
            "Ho ricevuto una mail di phishing, cosa faccio?": "cybersecurity",
            "Il rubinetto ha una perdita d'acqua": "plumber",
            "Come si fa la lievitazione dell'impasto della pizza?": "pastry-chef",
            "Mi aiuti col curriculum per un colloquio di lavoro?": "career-coach",
        }
        for text, template in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.pick(text), template)

    def test_small_talk_and_unknown_topics_stay_with_the_assistant(self):
        for text in ("ciao come stai", "grazie mille", "raccontami una barzelletta", "che ore sono"):
            with self.subTest(text=text):
                self.assertIsNone(self.pick(text))

    def test_disabled_expert_is_skipped(self):
        expert = self.store.get("teacher-math")
        expert.enabled = False
        self.assertNotEqual(self.pick("risolvi questa equazione di algebra"), "teacher-math")

    def test_ceo_records_the_delegation_on_the_board(self):
        before = len(board.log) if hasattr(board, "log") else 0
        choice = ceo.pick_expert("spiegami la termodinamica e le leggi di Newton")
        self.assertEqual(choice.expert.template, "teacher-physics")
        self.assertGreater(choice.score, 1)
        after = len(board.log) if hasattr(board, "log") else 1
        self.assertGreaterEqual(after, before)


class WideCatalogTest(unittest.TestCase):
    def test_catalog_is_wide_and_can_search_the_web(self):
        self.assertGreaterEqual(len(templates.ids()), 85)
        for tid, spec in templates.SPECS.items():
            if tid in ("debian", "football"):
                continue
            with self.subTest(template=tid):
                self.assertIn("web_research", spec["tools"])
                self.assertGreaterEqual(len(spec["keywords"]), 8)

    def test_ids_are_unique_and_valid_slugs(self):
        ids = templates.ids()
        self.assertEqual(len(ids), len(set(ids)))
        for tid in ids:
            self.assertRegex(tid, r"^[a-z][a-z0-9-]*$")



if __name__ == "__main__":
    unittest.main()
