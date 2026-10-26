import unittest
from server.core.decision.budget_ledger import DecisionBudgetLedger
from server.core.decision.calibration_metrics import (
    binary_brier_two_class,
    expected_calibration_error_10bin,
    multiclass_brier_score,
    paraphrase_consistency_metrics,
    ranked_probability_score,
    summarize_calibration,
    total_variation_distance,
)
from server.core.decision.combinations import (
    CalibrationWeightedCommittee,
    ConfidenceCascadeEngine,
)
from server.core.decision.composite_scorer import (
    compute_cost_axis,
    compute_field_relative_overfit_multiplier,
    compute_quadratic_floor_gate,
    compute_security_homeostasis_axis,
    compute_speed_axis,
    evaluate_composite_score,
    weighted_harmonic_mean,
)
from server.core.decision.contracts import (
    CanonicalDecisionTask,
    DecisionAxisScores,
    DecisionDomainException,
    DecisionPrimitive,
)
from server.core.decision.decision_engine import ContextDimension, decision_engine
from server.core.decision.scoring_math import (
    chance_corrected_choice,
    chance_corrected_rubric,
    chance_corrected_verdict,
    compute_conformal_set,
    debias_option_order,
    decompose_uncertainty,
    evaluate_verdict_band,
    fit_temperature_scaling,
    validate_distribution,
)


class TestNuxivaDecisionArbiter(unittest.TestCase):
    def test_two_band_distribution_validation(self) -> None:
        strict_res = validate_distribution({"a": 0.7002, "b": 0.3001}, ["a", "b"])
        self.assertTrue(strict_res.valid)
        self.assertTrue(strict_res.strict_valid)
        self.assertFalse(strict_res.renormalized)

        renorm_res = validate_distribution({"a": 0.69, "b": 0.30}, ["a", "b"])
        self.assertTrue(renorm_res.valid)
        self.assertFalse(renorm_res.strict_valid)
        self.assertTrue(renorm_res.renormalized)
        self.assertAlmostEqual(sum(renorm_res.probabilities.values()), 1.0, places=5)

        invalid_res = validate_distribution({"a": 0.50, "b": 0.30}, ["a", "b"])
        self.assertFalse(invalid_res.valid)

    def test_anti_leakage_task_guard(self) -> None:
        with self.assertRaises(DecisionDomainException):
            CanonicalDecisionTask(
                task_id="leak_test",
                primitive=DecisionPrimitive.VERDICT,
                state={"query": "hello", "ground_truth": "yes"},
                proposition="Safe?",
            )

    def test_verdict_abstention_band_and_chance_correction(self) -> None:
        label_hi, abst_hi, _ = evaluate_verdict_band(0.88)
        self.assertEqual(label_hi, "yes")
        self.assertFalse(abst_hi)

        label_lo, abst_lo, _ = evaluate_verdict_band(0.12)
        self.assertEqual(label_lo, "no")
        self.assertFalse(abst_lo)

        _, abst_mid, _ = evaluate_verdict_band(0.54)
        self.assertTrue(abst_mid)

        self.assertEqual(chance_corrected_verdict(0.50), 0.0)
        self.assertEqual(chance_corrected_verdict(1.0), 100.0)
        self.assertAlmostEqual(chance_corrected_choice(0.625, [4, 4]), 50.0, places=3)
        self.assertEqual(chance_corrected_rubric([0.0], [4], [5]), 100.0)

    def test_option_order_debiasing_and_conformal_set(self) -> None:
        fwd = {"opt_a": 0.64, "opt_b": 0.36}
        rev = {"opt_a": 0.49, "opt_b": 0.51}
        debiased, gap = debias_option_order(fwd, rev)
        self.assertAlmostEqual(sum(debiased.values()), 1.0, places=5)
        self.assertGreater(gap, 0.0)

        cset = compute_conformal_set({"x": 0.92, "y": 0.05, "z": 0.03}, alpha=0.10)
        self.assertTrue(cset.is_singleton)
        self.assertEqual(cset.included_labels, ["x"])

        unc = decompose_uncertainty([fwd, rev])
        self.assertGreaterEqual(unc.total_entropy, unc.aleatoric_entropy)
        self.assertGreaterEqual(unc.epistemic_divergence, 0.0)

    def test_temperature_scaling_and_calibration_metrics(self) -> None:
        dists = [{"yes": 0.9, "no": 0.1}, {"yes": 0.2, "no": 0.8}]
        golds = ["yes", "no"]
        temp = fit_temperature_scaling(dists, golds)
        self.assertGreaterEqual(temp, 0.05)
        self.assertLessEqual(temp, 5.0)

        brier_mc = multiclass_brier_score({"yes": 0.8, "no": 0.2}, "yes")
        brier_bin = binary_brier_two_class(0.8, True)
        self.assertAlmostEqual(brier_mc, brier_bin, places=5)

        tvd = total_variation_distance({"0": 0.5, "1": 0.5}, {"0": 1.0, "1": 0.0})
        self.assertAlmostEqual(tvd, 0.5, places=5)

        rps = ranked_probability_score({"0": 0.0, "1": 0.0, "2": 1.0}, gold_level=2, rubric_levels=3)
        self.assertEqual(rps, 0.0)

        ece = expected_calibration_error_10bin([0.9, 0.9], [True, True])
        self.assertAlmostEqual(ece, 0.1, places=4)

        agree, both_ok = paraphrase_consistency_metrics(
            ["g1", "g1", "g2", "g2"],
            ["yes", "yes", "a", "b"],
            ["yes", "yes", "a", "a"],
            [True, True, True, True],
        )
        self.assertEqual(agree, 0.5)
        self.assertEqual(both_ok, 0.5)

        summary = summarize_calibration(dists, golds)
        self.assertGreater(summary.pooled_calibration_score, 70.0)

    def test_five_axis_harmonic_composite_and_floor_gates(self) -> None:
        s_axis = compute_speed_axis(80.0, 95.0)
        c_axis = compute_cost_axis(0.0005)
        sec_axis = compute_security_homeostasis_axis(1.0, 0.0, [0.5, 0.1, 0.8, 0.1], 1.0)
        self.assertEqual(s_axis, 100.0)
        self.assertEqual(c_axis, 100.0)
        self.assertGreater(sec_axis, 90.0)

        overfit = compute_field_relative_overfit_multiplier(90.0, 65.0, field_median_gap=2.0)
        self.assertLess(overfit, 1.0)

        axes_high = DecisionAxisScores(
            intelligence=88.0,
            calibration=86.0,
            speed=94.0,
            cost=96.0,
            security_homeostasis=95.0,
        )
        eval_high = evaluate_composite_score(
            axes=axes_high,
            preset="NUXIVA_5AXIS",
            strata_scores={"open:verdict:easy": [100.0, 90.0], "sealed:choice:hard": [80.0, 85.0]},
        )
        self.assertEqual(eval_high.floor_gate_multiplier, 1.0)
        self.assertGreater(eval_high.composite_score, 85.0)
        self.assertIsNotNone(eval_high.bootstrap_ci)

        axes_low = DecisionAxisScores(
            intelligence=25.0,
            calibration=80.0,
            speed=80.0,
            cost=80.0,
            security_homeostasis=80.0,
        )
        gate_low = compute_quadratic_floor_gate(axes_low, intelligence_floor=50.0)
        self.assertAlmostEqual(gate_low, 0.25, places=4)
        self.assertEqual(weighted_harmonic_mean([0.0, 90.0], [0.5, 0.5]), 0.0)

    def test_confidence_cascade_and_committee(self) -> None:
        cascade = ConfidenceCascadeEngine(default_threshold=0.80)
        tuned = cascade.fit_optimal_threshold(
            fast_confidences=[0.95, 0.92, 0.55, 0.60],
            fast_predictions=["a", "b", "wrong", "d"],
            deep_predictions=["a", "b", "c", "d"],
            gold_labels=["a", "b", "c", "d"],
            target_accuracy_retention=0.99,
        )
        self.assertGreaterEqual(tuned["cascade_accuracy"], 0.99)

        committee = CalibrationWeightedCommittee(competence_exponent=0.5)
        outcome = committee.combine(
            members=[
                ("model_alpha", {"yes": 0.85, "no": 0.15}, 92.0, 90.0),
                ("model_beta", {"yes": 0.75, "no": 0.25}, 84.0, 82.0),
            ],
            expected_labels=["yes", "no"],
        )
        self.assertEqual(outcome.consensus_label, "yes")
        self.assertGreater(outcome.consensus_confidence, 0.75)

    def test_hmac_budget_ledger_reservations_and_integrity(self) -> None:
        ledger = DecisionBudgetLedger(cap_usd=1.0)
        r1 = ledger.reserve("adapter_1", worst_case_usd=0.40)
        self.assertEqual(ledger.committed_usd(), 0.40)

        with self.assertRaises(DecisionDomainException):
            ledger.reserve("adapter_2", worst_case_usd=0.70)

        with self.assertRaises(DecisionDomainException):
            ledger.settle(r1.reservation_id, actual_usd=0.50)

        ledger.settle(r1.reservation_id, actual_usd=0.15, actual_tokens=120)
        self.assertEqual(ledger.committed_usd(), 0.15)
        self.assertTrue(ledger.verify_integrity())

    def test_decision_engine_end_to_end_and_conformance(self) -> None:
        ctx = ContextDimension(user_role="user_primary")
        dec = decision_engine.evaluate("invia una mail urgente a Marco", ctx)
        self.assertEqual(dec.selected_action.action_id, "gmail_send_message")
        self.assertIsNotNone(dec.conformal_set)

        conformance = decision_engine.run_conformance()
        self.assertTrue(conformance.passed_all)
        self.assertGreaterEqual(conformance.total_checks, 10)

        bench = decision_engine.run_benchmark("NUXIVA_5AXIS")
        self.assertGreater(bench["evaluation"]["composite_score"], 70.0)


if __name__ == "__main__":
    unittest.main()
