use super::types::{Candidate, Decision, SlowReason, Thresholds, Verdict};

fn slow(reason: SlowReason, candidate: Option<&Candidate<'_>>) -> Decision {
    Decision {
        verdict: Verdict::SlowPath,
        reason: Some(reason),
        neuron_id: candidate.map(|c| c.neuron.id.clone()),
        positive_similarity: candidate.map_or(0.0, |c| c.positive_similarity),
        negative_similarity: candidate.map_or(0.0, |c| c.negative_similarity),
        synaptic_weight: candidate.map_or(0.0, |c| c.neuron.weight),
    }
}

#[must_use]
pub fn decide(candidate: Option<&Candidate<'_>>, thresholds: &Thresholds) -> Decision {
    let Some(found) = candidate else {
        return slow(SlowReason::NoNeurons, None);
    };
    let similarity = found.positive_similarity;
    let weight = found.neuron.weight;
    if found.negative_similarity >= thresholds.inhibition_limit {
        return slow(SlowReason::Inhibited, candidate);
    }
    if similarity < thresholds.grey_similarity {
        return slow(SlowReason::LowSimilarity, candidate);
    }
    let verdict = if similarity >= thresholds.fast_similarity && weight >= thresholds.fast_weight {
        Verdict::FastPath
    } else if weight >= thresholds.grey_weight {
        Verdict::GreyZone
    } else {
        return slow(SlowReason::LowWeight, candidate);
    };
    Decision {
        verdict,
        reason: None,
        neuron_id: Some(found.neuron.id.clone()),
        positive_similarity: similarity,
        negative_similarity: found.negative_similarity,
        synaptic_weight: weight,
    }
}

#[cfg(test)]
mod tests {
    use super::{Candidate, SlowReason, Thresholds, Verdict, decide};
    use crate::hippocampus::types::Neuron;

    fn neuron(weight: f32) -> Neuron {
        Neuron {
            id: "light.on".to_owned(),
            weight,
            dendrites: vec![vec![1.0]],
            inhibitions: Vec::new(),
        }
    }

    fn verdict_for(similarity: f32, negative: f32, weight: f32) -> (Verdict, Option<SlowReason>) {
        let subject = neuron(weight);
        let candidate = Candidate {
            neuron: &subject,
            positive_similarity: similarity,
            negative_similarity: negative,
        };
        let decision = decide(Some(&candidate), &Thresholds::default());
        (decision.verdict, decision.reason)
    }

    #[test]
    fn strong_match_with_trusted_synapse_takes_the_fast_path() {
        assert_eq!(verdict_for(0.90, 0.10, 0.80), (Verdict::FastPath, None));
        assert_eq!(verdict_for(0.85, 0.59, 0.75), (Verdict::FastPath, None));
    }

    #[test]
    fn intermediate_similarity_or_weight_needs_quick_verification() {
        assert_eq!(verdict_for(0.80, 0.10, 0.60), (Verdict::GreyZone, None));
        assert_eq!(verdict_for(0.90, 0.10, 0.60), (Verdict::GreyZone, None));
    }

    #[test]
    fn weak_inhibited_or_untrusted_matches_go_to_the_slow_path() {
        assert_eq!(
            verdict_for(0.60, 0.10, 0.90),
            (Verdict::SlowPath, Some(SlowReason::LowSimilarity))
        );
        assert_eq!(
            verdict_for(0.95, 0.60, 0.90),
            (Verdict::SlowPath, Some(SlowReason::Inhibited))
        );
        assert_eq!(
            verdict_for(0.80, 0.10, 0.40),
            (Verdict::SlowPath, Some(SlowReason::LowWeight))
        );
    }

    #[test]
    fn no_candidate_means_no_neurons() {
        let decision = decide(None, &Thresholds::default());
        assert_eq!(decision.verdict, Verdict::SlowPath);
        assert_eq!(decision.reason, Some(SlowReason::NoNeurons));
        assert_eq!(decision.neuron_id, None);
    }
}
