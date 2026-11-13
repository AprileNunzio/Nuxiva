import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agenti import _mastery, _study
from agenti._mastery import Ledger, MasteryError

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

NATIVE = nuxiva_native is not None and hasattr(nuxiva_native, "mastery_evaluate")
DAY = 86_400


def runs(tier, scores, at):
    return [{"tier": tier, "score": s, "at": at} for s in scores]


class EvaluateTest(unittest.TestCase):
    def test_no_evidence_means_novice(self):
        state = _mastery.evaluate_python([], 0)
        self.assertEqual((state["level"], state["rank"], state["next"]), (0, "novice", {"tier": 0, "kind": "advance"}))

    def test_levels_need_contiguous_passed_tiers(self):
        self.assertEqual(_mastery.evaluate_python(runs(5, [1, 1, 1], 1), 1)["level"], 0)
        both = runs(0, [0.9] * 3, 1) + runs(1, [0.8] * 3, 1)
        self.assertEqual(_mastery.evaluate_python(both, 2)["level"], 2)

    def test_stale_tier_is_reviewed_and_old_skill_lapses(self):
        old = runs(0, [0.9] * 3, 0)
        self.assertEqual(_mastery.evaluate_python(old, 40 * DAY)["next"], {"tier": 0, "kind": "review"})
        self.assertEqual(_mastery.evaluate_python(old, 100 * DAY)["level"], 0)

    def test_hostile_attempts_are_neutralised(self):
        junk = [{"tier": "x"}, {"tier": 99, "score": 1, "at": 0}, {"tier": 0, "score": float("nan"), "at": 0}, {"tier": True, "score": 1, "at": 0}]
        self.assertEqual(_mastery.evaluate_python(junk, 0)["level"], 0)

    @unittest.skipUnless(NATIVE, "native wheel missing")
    def test_native_and_python_agree(self):
        rng = random.Random(7)
        for _ in range(200):
            attempts = [{"tier": rng.randrange(0, 4), "score": rng.choice([0.0, 0.5, 0.7, 0.9, 1.0]), "at": rng.randrange(0, 120 * DAY)}
                        for _ in range(rng.randrange(0, 40))]
            now = rng.randrange(0, 150 * DAY)
            native = json.loads(nuxiva_native.mastery_evaluate(json.dumps(_mastery._clean(attempts)), now))
            python = _mastery.evaluate_python(attempts, now)
            self.assertEqual(native["level"], python["level"])
            self.assertEqual(native["next"], python["next"])
            self.assertEqual(native["rank"], python["rank"])
            self.assertAlmostEqual(native["recent_mean"], python["recent_mean"], places=9)

    @unittest.skipUnless(NATIVE, "native wheel missing")
    def test_native_refuses_oversized_input(self):
        with self.assertRaises(ValueError):
            nuxiva_native.mastery_evaluate("[" + "0," * 40_000 + "0]", 0)


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.book = Ledger(Path(tempfile.mkdtemp()) / "mastery")

    def test_record_and_standing_roundtrip(self):
        for _ in range(3):
            state = self.book.record("particles", "objects", 0, 0.9, "ok", 10)
        self.assertEqual(state["level"], 1)
        self.assertEqual(self.book.topics("particles"), ["objects"])
        self.assertEqual(self.book.lessons("particles")[0]["text"], "ok")

    def test_files_are_private_and_names_checked(self):
        self.book.record("particles", "objects", 0, 1.0, "", 1)
        mode = (self.book.root / "particles.json").stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)
        for bad in ("../x", "A b", "", "x" * 60):
            with self.assertRaises(MasteryError):
                self.book.record(bad, "objects", 0, 1.0)
            with self.assertRaises(MasteryError):
                self.book.record("particles", bad, 0, 1.0)

    def test_bad_tier_and_scores_are_handled(self):
        with self.assertRaises(MasteryError):
            self.book.record("particles", "objects", 10, 1.0)
        with self.assertRaises(MasteryError):
            self.book.record("particles", "objects", True, 1.0)
        self.book.record("particles", "objects", 0, float("inf"), "", 1)
        self.assertEqual(self.book.standing("particles", "objects", 1)["recent_mean"], 0.0)

    def test_corrupted_file_starts_clean(self):
        self.book.record("particles", "objects", 0, 1.0, "", 1)
        (self.book.root / "particles.json").write_text("{rotto", "utf-8")
        self.assertEqual(self.book.standing("particles", "objects", 1)["attempts"], 0)

    def test_history_and_lessons_are_bounded(self):
        for i in range(450):
            self.book.record("particles", "objects", 0, 0.5, "lezione " * 100, i)
        self.assertEqual(self.book.standing("particles", "objects", 450)["attempts"], _mastery.MAX_ATTEMPTS)
        self.assertLessEqual(len(self.book.lessons("particles", 1000)), _mastery.MAX_LESSONS)
        self.assertLessEqual(len(self.book.lessons("particles", 1)[0]["text"]), _mastery.MAX_LESSON_TEXT)


class Provider:
    TOPICS = ("alpha",)

    def __init__(self, score=0.9, fail=False):
        self.score, self.fail = score, fail

    def make(self, topic, tier):
        return _study.Exercise(topic, tier, "p")

    async def attempt(self, exercise):
        if self.fail:
            raise RuntimeError("giù")
        return exercise

    def grade(self, exercise, result):
        return self.score, "imparato"


class StudyTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.book = Ledger(Path(tempfile.mkdtemp()) / "mastery")

    async def test_session_climbs_with_real_results(self):
        done = await _study.session("tutor", Provider(0.9), 6, self.book)
        self.assertEqual(len(done), 6)
        self.assertEqual(done[-1]["after"], 2)
        self.assertEqual(done[0]["tier"], 0)
        self.assertEqual(done[3]["tier"], 1)

    async def test_failures_never_raise_the_level(self):
        done = await _study.session("tutor", Provider(0.9, fail=True), 5, self.book)
        self.assertEqual({d["after"] for d in done}, {0})

    async def test_provider_without_topics_does_nothing(self):
        class Empty:
            TOPICS = ()

        self.assertIsNone(await _study.study("tutor", Empty(), None, self.book))
        self.assertEqual(await _study.session("tutor", Empty(), 3, self.book), [])

    async def test_rounds_are_capped(self):
        done = await _study.session("tutor", Provider(), 1000, self.book)
        self.assertEqual(len(done), 20)


class ParticleExercisesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from agenti.particles import exercises
        self.exercises = exercises
        self.book = Ledger(Path(tempfile.mkdtemp()) / "mastery")

    async def test_known_animal_is_graded_high_and_empty_result_zero(self):
        from agenti.particles import forma_design
        spec = forma_design.build(forma_design.draft("gatto"))[0]
        exercise = self.exercises.make("objects", 2)
        score, _ = self.exercises.grade(exercise, spec)
        self.assertGreaterEqual(score, 0.9)
        self.assertEqual(self.exercises.grade(exercise, None)[0], 0.0)

    async def test_session_with_the_instant_designer_records_progress(self):
        from agenti.particles import forma_design

        async def create(concept):
            return forma_design.build(forma_design.draft("gatto"))[0]

        with mock.patch.object(forma_design, "create", create):
            done = await _study.session("particles", self.exercises, 3, self.book)
        self.assertEqual(len(done), 3)
        self.assertEqual(self.book.standing("particles", "objects")["attempts"], 3)

    def test_ladder_covers_every_tier(self):
        self.assertEqual(len(self.exercises.LADDER), _mastery.TIERS)
        self.assertEqual(len(self.exercises.MIN_PARTS), _mastery.TIERS)


class RunnerTest(unittest.IsolatedAsyncioTestCase):
    def test_the_particle_agent_is_discovered(self):
        from agenti import _study_runner
        found = [ident for ident, _ in _study_runner.providers()]
        for ident in ("particles", "ear", "chat"):
            self.assertIn(ident, found)

    def test_interval_is_bounded_and_can_be_disabled(self):
        from agenti import _study_runner
        for raw, want in (("0", 0.0), ("-3", 0.0), ("0.1", 1.0), ("9999", 168.0), ("abc", 6.0), ("12", 12.0)):
            with mock.patch.dict("os.environ", {"NUXIVA_AGENT_STUDY_HOURS": raw}):
                self.assertEqual(_study_runner._hours(), want)

    async def test_round_continues_after_a_failing_agent(self):
        from agenti import _study_runner

        async def session(ident, module, rounds):
            if ident == "rotto":
                raise RuntimeError("giù")
            return [{"agent": ident}]

        with mock.patch.object(_study_runner, "providers", lambda: [("rotto", None), ("sano", None)]), \
                mock.patch.object(_study, "session", session):
            self.assertEqual(await _study_runner.round_all(), [{"agent": "sano"}])


class MeasurableAgentsTest(unittest.IsolatedAsyncioTestCase):
    async def test_ear_vote_recovers_light_noise_and_degrades_with_heavy_noise(self):
        from agenti.ear import exercises
        scores = []
        for tier in (0, 9):
            total = 0.0
            for _ in range(20):
                exercise = exercises.make("consensus", tier)
                total += exercises.grade(exercise, await exercises.attempt(exercise))[0]
            scores.append(total / 20)
        self.assertGreater(scores[0], 0.85)
        self.assertLess(scores[1], scores[0])

    async def test_ear_exercise_is_reproducible_from_its_seed_and_refuses_junk(self):
        from agenti.ear import exercises
        exercise = exercises.make("consensus", 4)
        first, second = await exercises.attempt(exercise), await exercises.attempt(exercise)
        self.assertEqual(first, second)
        self.assertEqual(exercises.grade(exercise, "boh"), (0.0, ""))

    async def test_chat_weather_ladder_scores_real_behaviour(self):
        from agenti.chat import exercises
        easy = exercises.make("weather_requests", 0)
        self.assertEqual(exercises.grade(easy, await exercises.attempt(easy))[0], 1.0)
        self.assertEqual(exercises.grade(easy, [])[0], 0.0)
        self.assertEqual(len(exercises.LADDER), _mastery.TIERS)
        wrong = [(text, "Atlantide", 5) for text, _, _ in easy.data["cases"]]
        score, lesson = exercises.grade(easy, wrong)
        self.assertEqual(score, 0.0)
        self.assertIn("atteso", lesson)

    async def test_sessions_run_end_to_end_for_both(self):
        from agenti.chat import exercises as chat
        from agenti.ear import exercises as ear
        book = Ledger(Path(tempfile.mkdtemp()) / "mastery")
        for ident, module in (("chat", chat), ("ear", ear)):
            done = await _study.session(ident, module, 3, book)
            self.assertEqual(len(done), 3)
            self.assertEqual(book.standing(ident, module.TOPICS[0])["attempts"], 3)


if __name__ == "__main__":
    unittest.main()
