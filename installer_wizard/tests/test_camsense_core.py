import unittest

import numpy as np

from features.camsense import classifier, model


def unit(values):
    array = np.array(values, dtype=np.float64)
    return (array / np.linalg.norm(array)).tolist()


SAMPLES = {"aperta": [unit([1, 0, 0]), unit([0.95, 0.1, 0])], "chiusa": [unit([0, 1, 0]), unit([0.1, 0.95, 0])]}


class ClassifierTests(unittest.TestCase):

    def test_clear_match_returns_the_label(self):
        verdict = classifier.classify(SAMPLES, unit([1, 0.05, 0]))
        self.assertEqual((verdict.label, verdict.reason), ("aperta", "ok"))

    def test_unknown_scene_is_not_forced_into_a_state(self):
        verdict = classifier.classify(SAMPLES, unit([0, 0, 1]))
        self.assertEqual((verdict.label, verdict.reason), ("", "unlike_any_state"))

    def test_ambiguous_scene_is_reported(self):
        close = {"aperta": [unit([1, 0.3, 0])], "chiusa": [unit([0.3, 1, 0])]}
        verdict = classifier.classify(close, unit([1, 1, 0]))
        self.assertEqual((verdict.label, verdict.reason), ("", "ambiguous"))

    def test_needs_at_least_two_states(self):
        self.assertEqual(classifier.classify({"aperta": SAMPLES["aperta"]}, unit([1, 0, 0])).reason, "needs_two_states")
        self.assertEqual(classifier.classify({}, unit([1, 0, 0])).label, "")


class ModelTests(unittest.TestCase):

    def test_names_and_labels_are_validated(self):
        self.assertEqual(model.slug("Porta Garage"), "porta-garage")
        self.assertEqual(model.label_of("  Aperta "), "aperta")
        for bad in ("", "<x>", "a" * 80):
            with self.assertRaises(model.SenseError):
                model.label_of(bad)

    def test_regions_must_stay_inside_the_frame(self):
        self.assertEqual(model.region(None), [0.0, 0.0, 1.0, 1.0])
        self.assertEqual(model.region([0.1, 0.1, 0.5, 0.5]), [0.1, 0.1, 0.5, 0.5])
        for bad in ([0.9, 0.9, 0.5, 0.5], [0, 0, 0.001, 1], ["a", 1, 1, 1], [-1, 0, 1, 1]):
            with self.assertRaises(model.SenseError):
                model.region(bad)


if __name__ == "__main__":
    unittest.main()
