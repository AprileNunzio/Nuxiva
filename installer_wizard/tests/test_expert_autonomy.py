import asyncio
import unittest
import unittest.mock

from features.experts import autonomy, service
from tests.test_experts import IsolatedStore


SPEC = {"role": "Esperto di apicoltura urbana", "specialty": "Alveari in città, normativa e gestione stagionale",
        "knowledge": ["Posizionamento delle arnie", "Denuncia degli alveari", "Raccolta del miele"], "icon": "🐝", "coding": False}
QUESTION = "Come devo sistemare un alveare sul balcone di casa?"


class AutonomyCase(IsolatedStore):
    def setUp(self):
        super().setUp()
        for patch in (unittest.mock.patch.object(autonomy, "experts", self.store),
                      unittest.mock.patch.object(autonomy, "env_get", lambda key, default="": "1")):
            patch.start()
            self.addCleanup(patch.stop)
        autonomy._stamps.clear()

    def run_with(self, spec, text=QUESTION):
        async def fake(*args, **kwargs):
            if isinstance(spec, Exception):
                raise spec
            return spec
        with unittest.mock.patch("features.actions.common.llm", fake):
            return asyncio.run(autonomy.create_for(text))


class QuestionFilterTest(unittest.TestCase):
    def test_only_real_questions_qualify(self):
        self.assertTrue(autonomy.worth_asking(QUESTION))
        for text in ("ciao", "come stai?", "accendi la luce del salotto", "x" * 500 + "?", ""):
            with self.subTest(text=text[:20]):
                self.assertFalse(autonomy.worth_asking(text))


class CreateTest(AutonomyCase):
    def test_creates_a_persistent_expert_with_web_research(self):
        expert = self.run_with(SPEC)
        self.assertEqual(expert.template, autonomy.TEMPLATE)
        self.assertIn("web_research", expert.tools)
        self.assertNotIn("dev_write", expert.tools)
        self.assertEqual(len(self.store.all()), 1)

    def test_coding_questions_get_development_tools(self):
        expert = self.run_with({**SPEC, "role": "Sviluppatore Rust embedded", "coding": True})
        self.assertIn("dev_write", expert.tools)

    def test_same_role_is_reused_not_duplicated(self):
        first = self.run_with(SPEC)
        second = self.run_with(SPEC)
        self.assertEqual(first.id, second.id)
        self.assertEqual(len(self.store.all()), 1)

    def test_chitchat_and_broken_answers_create_nothing(self):
        for spec in ({"role": ""}, {"role": "Boh"}, "testo", None, RuntimeError("down")):
            with self.subTest(spec=str(spec)[:20]):
                self.assertIsNone(self.run_with(spec))
        self.assertEqual(self.store.all(), [])

    def test_markup_is_stripped_from_generated_text(self):
        expert = self.run_with({**SPEC, "role": "Esperto <script>x</script> di api"})
        self.assertNotIn("<", expert.role)

    def test_daily_budget_is_enforced(self):
        with unittest.mock.patch.object(autonomy, "PER_DAY", 1):
            self.assertIsNotNone(self.run_with(SPEC))
            self.assertIsNone(self.run_with({**SPEC, "role": "Esperto di tulipani"}))

    def test_switch_off_disables_creation(self):
        with unittest.mock.patch.object(autonomy, "env_get", lambda key, default="": "0"):
            self.assertIsNone(self.run_with(SPEC))


class WiringTest(AutonomyCase):
    def test_unmatched_question_is_answered_by_a_new_expert(self):
        from features.chat import assistant
        from features.experts import commands

        async def fake_run(expert, text):
            return f"risposta di {expert.role}", {"mode": "face"}

        with unittest.mock.patch("features.team.ceo.ceo.pick_expert", return_value=None), \
                unittest.mock.patch.object(commands, "run", fake_run):
            async def go():
                async def fake(*args, **kwargs):
                    return SPEC
                with unittest.mock.patch("features.actions.common.llm", fake):
                    return await assistant._delegate(QUESTION)
            label, speech, ui = asyncio.run(go())
        self.assertIn("apicoltura", label)
        self.assertIn("risposta di", speech)

    def test_no_expert_and_no_creation_falls_through(self):
        from features.chat import assistant
        with unittest.mock.patch("features.team.ceo.ceo.pick_expert", return_value=None):
            self.assertIsNone(asyncio.run(assistant._delegate("ok")))


if __name__ == "__main__":
    unittest.main()
