import itertools
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear"), str(ROOT / "agenti" / "percezione" / "biometrics")):
    if p not in sys.path:
        sys.path.insert(0, p)

import native_core
import embeddings as emb
import voiceprint
from agenti.ear.speakers import SpeakerContext, turn_fields

NATIVE = native_core.load()
READY = NATIVE is not None and all(hasattr(NATIVE, n) for n in ("RustVoiceBook", "RustVoiceTracker", "ear_split_turns"))
DIM = 64


def person(rng, base, count, spread):
    return emb.unit_rows(base + spread * rng.standard_normal((count, DIM)))


def python_verdict(samples, probe, base=0.62, margin=0.06, twin_margin=0.12, twin_sim=0.5):
    centres = {s: emb.centroid(r) for s, r in samples.items()}
    limits = {s: emb.person_threshold(r, base) for s, r in samples.items()}
    scores = {s: voiceprint.person_score(r, centres[s], probe) for s, r in samples.items()}
    return scores, emb.decide(scores, limits, base, margin, twin_margin, emb.twin_pairs(centres, twin_sim)), limits


@unittest.skipUnless(READY, "modulo nativo ear-core non installato")
class VoiceBookParityTest(unittest.TestCase):

    def test_scores_thresholds_and_verdicts_match_python(self):
        rng = np.random.default_rng(11)
        for trial, (count, spread, twin) in enumerate(itertools.product((2, 5, 8, 12), (0.2, 0.5), (False, True))):
            anna = rng.standard_normal(DIM)
            luca = anna + 0.4 * rng.standard_normal(DIM) if twin else rng.standard_normal(DIM)
            samples = {"anna": person(rng, anna, count, spread), "luca": person(rng, luca, count, spread),
                       "zoe": person(rng, rng.standard_normal(DIM), 3, spread)}
            book = voiceprint.build_book(samples)
            self.assertIsNotNone(book)
            probes = [emb.unit(anna + spread * rng.standard_normal(DIM)), emb.unit(luca + 0.3 * rng.standard_normal(DIM)),
                      emb.unit(0.5 * (anna + luca)), emb.unit(rng.standard_normal(DIM))]
            for index, probe in enumerate(probes):
                scores, expected, limits = python_verdict(samples, probe)
                got = book.verdict(probe.astype(np.float32).tolist())
                with self.subTest(trial=trial, probe=index):
                    rust_scores = dict(book.scores(probe.astype(np.float32).tolist()))
                    for slug in samples:
                        self.assertAlmostEqual(rust_scores[slug], scores[slug], places=4)
                        self.assertAlmostEqual(book.limit(slug), limits[slug], places=4)
                    for key in ("slug", "best", "second", "ambiguous", "reason"):
                        self.assertEqual(got[key], expected[key], key)
                    self.assertAlmostEqual(got["score"], expected["score"], places=4)

    def test_voiceprints_delegates_to_rust(self):
        rng = np.random.default_rng(3)
        anna = rng.standard_normal(DIM)
        samples = {"anna": person(rng, anna, 6, 0.3), "luca": person(rng, rng.standard_normal(DIM), 6, 0.3)}
        prints = voiceprint.Voiceprints()
        prints.samples = samples
        prints.centres = {s: emb.centroid(r) for s, r in samples.items()}
        prints.limits = {s: emb.person_threshold(r, voiceprint.match_base()) for s, r in samples.items()}
        prints.twins = emb.twin_pairs(prints.centres, voiceprint.twin_similarity())
        prints.book = voiceprint.build_book(samples)
        probe = emb.unit(anna + 0.3 * rng.standard_normal(DIM))
        rust, python = prints.verdict(probe), prints._py_verdict(probe)
        self.assertEqual(rust["slug"], "anna")
        self.assertEqual((rust["slug"], rust["reason"]), (python["slug"], python["reason"]))

    def test_invalid_probes_are_rejected(self):
        book = NATIVE.RustVoiceBook()
        with self.assertRaises(ValueError):
            book.verdict([])
        self.assertFalse(book.set_person("Not Valid", [[0.1] * 8]))
        self.assertEqual(book.verdict([0.1] * 8)["reason"], "nessuno")


class FakePrints:

    def __init__(self):
        rng = np.random.default_rng(5)
        self.voices = {1: emb.unit(rng.standard_normal(DIM)), 2: emb.unit(rng.standard_normal(DIM))}
        self.added = []

    def embed(self, audio):
        marker = int(round(float(np.median(audio)) * 10))
        return self.voices.get(marker)

    def identify(self, probe):
        if probe is None:
            return None, 0.0
        return ("anna", 0.8) if float(probe @ self.voices[1]) > 0.9 else (None, 0.1)

    def verdict(self, probe):
        slug, score = self.identify(probe)
        return {"slug": slug, "score": score}

    def attest(self, probe, seconds, programme, windows=None):
        slug, score = self.identify(probe)
        verified = slug is not None and seconds >= 1.2 and not programme
        return {"slug": slug if verified else None, "verified": verified, "foreign": False, "score": score,
                "needed": 0.7, "reason": "ok" if verified else "rifiutata"}

    def count(self, slug):
        return 5

    def add(self, slug, probe, source):
        self.added.append(slug)


@unittest.skipUnless(READY, "modulo nativo ear-core non installato")
class SpeakerContextTest(unittest.TestCase):

    def test_two_voices_in_one_sentence_are_split(self):
        prints = FakePrints()
        context = SpeakerContext(prints)
        audio = np.concatenate([np.full(16000 * 3, 0.1), np.full(16000 * 2, 0.2)]).astype(np.float32)
        speech, mixed = context.dominant(audio)
        self.assertTrue(mixed)
        self.assertAlmostEqual(float(np.median(speech)), 0.1, places=5)
        slug, score, info = context.identify(audio, "anna")
        self.assertEqual(slug, "anna")
        self.assertTrue(info["mixed_speakers"])
        self.assertEqual(prints.added, [])
        self.assertEqual(info["voice_match"], "anna")
        self.assertNotIn("voice_known", info)

    def test_turns_are_tracked_across_sentences(self):
        prints = FakePrints()
        context = SpeakerContext(prints)
        first = context.identify(np.full(16000 * 2, 0.1, dtype=np.float32), "anna")[2]
        second = context.identify(np.full(16000 * 2, 0.1, dtype=np.float32), None)[2]
        other = context.identify(np.full(16000 * 2, 0.2, dtype=np.float32), None)[2]
        self.assertEqual(prints.added, ["anna"])
        self.assertEqual(first["voice_label"], second["voice_label"])
        self.assertTrue(second["same_speaker"])
        self.assertTrue(other["new_voice"])
        self.assertEqual(other["voices_active"], 2)
        self.assertEqual(context.active(), 2)


@unittest.skipUnless(READY, "modulo nativo ear-core non installato")
class RadioIsNeverLearnedTest(unittest.TestCase):

    def test_unrecognised_voice_is_not_added_to_the_owner_profile(self):
        prints = FakePrints()
        context = SpeakerContext(prints)
        slug, _, info = context.identify(np.full(16000 * 2, 0.2, dtype=np.float32), "anna")
        self.assertIsNone(slug)
        self.assertEqual(prints.added, [])
        self.assertFalse(info["voice_verified"])

    def test_nothing_is_learned_while_music_or_a_programme_plays(self):
        prints = FakePrints()
        context = SpeakerContext(prints)
        slug, _, info = context.identify(np.full(16000 * 2, 0.1, dtype=np.float32), "anna", True)
        self.assertIsNone(slug)
        self.assertEqual(prints.added, [])
        self.assertFalse(info["voice_verified"])


class FallbackTest(unittest.TestCase):

    def test_without_native_module(self):
        with mock.patch.object(native_core, "symbol", return_value=None):
            context = SpeakerContext(FakePrints())
            self.assertIsNone(voiceprint.build_book({"anna": np.ones((2, DIM), dtype=np.float32)}))
        slug, _, info = context.identify(np.full(16000 * 4, 0.1, dtype=np.float32), None)
        self.assertEqual(slug, "anna")
        self.assertEqual(info, {"mixed_speakers": False, "voice_verified": True, "voice_reason": "ok"})
        self.assertEqual(context.active(), 0)


class FakeTracker:

    def observe(self, probe, now, known=None):
        return {"voice_label": 1, "voice_known": known, "new_voice": False, "same_speaker": True,
                "voices_active": 1, "voice_similarity": 0.9}


class TurnFieldsTest(unittest.TestCase):

    def test_tracker_match_never_collides_with_voice_known(self):
        prints = FakePrints()
        context = SpeakerContext(prints)
        context.tracker, context.split = FakeTracker(), None
        slug, _, turn = context.identify(np.full(16000 * 2, 0.1, dtype=np.float32), None)
        self.assertEqual(slug, "anna")
        self.assertNotIn("voice_known", turn)
        self.assertEqual(turn["voice_match"], "anna")
        event = turn | {"type": "transcript", "voice_known": True}
        self.assertIs(event["voice_known"], True)
        self.assertTrue(event["same_speaker"])

    def test_missing_observation_is_empty(self):
        self.assertEqual(turn_fields(None), {})
        self.assertEqual(turn_fields({"voice_known": None, "new_voice": True}), {"voice_match": None, "new_voice": True})


if __name__ == "__main__":
    unittest.main()
