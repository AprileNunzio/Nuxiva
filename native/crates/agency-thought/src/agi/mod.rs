use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::ThoughtError;

pub const SURPRISE_GOAL_THRESHOLD_BPS: u32 = 3_000;
pub const MAX_WORLD_TRANSITIONS: usize = 256;
pub const MAX_STRATEGIES: usize = 128;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WorldTransition {
    pub state_key: String,
    pub action_key: String,
    pub predicted_next_key: String,
    pub observed_next_key: String,
    pub latency_ms: u64,
    pub token_cost: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TransitionBelief {
    pub state_key: String,
    pub action_key: String,
    pub expected_outcome_key: String,
    pub observations: u32,
    pub prediction_errors: u32,
    pub surprise_bps: u32,
    pub epistemic_uncertainty_bps: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IntrinsicGoal {
    pub goal_id: String,
    pub target_state_key: String,
    pub target_action_key: String,
    pub directive_key: String,
    pub expected_information_gain_bps: u32,
    pub priority_bps: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PolicyCandidate {
    pub policy_id: String,
    pub action_key: String,
    pub pragmatic_value_bps: u32,
    pub epistemic_value_bps: u32,
    pub token_cost: u64,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EvaluatedPolicy {
    pub policy_id: String,
    pub action_key: String,
    pub expected_free_energy_score: i64,
    pub selected: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AlgorithmicStrategy {
    pub domain_key: String,
    pub strategy_id: String,
    pub generation: u32,
    pub success_rate_bps: u32,
    pub mean_latency_ms: u64,
    pub mean_token_cost: u64,
    pub code_complexity_bytes: usize,
    pub proof_digest: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GodelUpgradeVerdict {
    pub domain_key: String,
    pub upgraded: bool,
    pub active_strategy_id: String,
    pub active_generation: u32,
    pub compression_gain_bps: u32,
    pub latency_gain_bps: u32,
    pub token_savings_bps: u32,
    pub reason_key: String,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct AutonomousAgiKernel {
    beliefs: BTreeMap<String, TransitionBelief>,
    strategies: BTreeMap<String, AlgorithmicStrategy>,
}

fn validate_clean_key(raw: &str, field: &'static str) -> Result<String, ThoughtError> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err(ThoughtError::InvalidText {
            field,
            reason: "must not be empty",
        });
    }
    if trimmed.len() > 240 {
        return Err(ThoughtError::InvalidText {
            field,
            reason: "exceeds maximum length",
        });
    }
    if trimmed
        .chars()
        .any(|c| c.is_control() || c == '\0' || c == '\u{202e}')
    {
        return Err(ThoughtError::InvalidText {
            field,
            reason: "contains forbidden control characters",
        });
    }
    Ok(trimmed.to_owned())
}

fn ratio_gain_bps(old_val: u64, new_val: u64) -> u32 {
    if old_val == 0 || new_val >= old_val {
        return 0;
    }
    let diff = old_val.saturating_sub(new_val);
    let scaled = diff
        .saturating_mul(10_000)
        .checked_div(old_val)
        .unwrap_or(0);
    u32::try_from(scaled.min(10_000)).unwrap_or(10_000)
}

pub fn select_minimal_free_energy_policy(
    candidates: &[PolicyCandidate],
) -> Result<Vec<EvaluatedPolicy>, ThoughtError> {
    if candidates.is_empty() {
        return Err(ThoughtError::EmptyCandidates);
    }
    if candidates.len() > 64 {
        return Err(ThoughtError::TooManyCandidates(64));
    }

    let mut evaluated = Vec::with_capacity(candidates.len());
    for cand in candidates {
        let clean_id = validate_clean_key(&cand.policy_id, "policy_id")?;
        let clean_act = validate_clean_key(&cand.action_key, "action_key")?;
        let pragmatic = i64::from(cand.pragmatic_value_bps.min(10_000));
        let epistemic = i64::from(cand.epistemic_value_bps.min(10_000));
        let token_penalty = i64::try_from(cand.token_cost.min(50_000) / 10).unwrap_or(5_000);
        let latency_penalty = i64::try_from(cand.latency_ms.min(60_000) / 20).unwrap_or(3_000);
        let efe_score = pragmatic
            .saturating_mul(6)
            .saturating_add(epistemic.saturating_mul(5))
            .saturating_sub(token_penalty)
            .saturating_sub(latency_penalty);

        evaluated.push(EvaluatedPolicy {
            policy_id: clean_id,
            action_key: clean_act,
            expected_free_energy_score: efe_score,
            selected: false,
        });
    }

    evaluated.sort_by(|a, b| {
        b.expected_free_energy_score
            .cmp(&a.expected_free_energy_score)
            .then_with(|| a.policy_id.cmp(&b.policy_id))
    });

    if let Some(first) = evaluated.first_mut() {
        first.selected = true;
    }

    Ok(evaluated)
}

impl AutonomousAgiKernel {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn observe_transition(
        &mut self,
        transition: &WorldTransition,
    ) -> Result<(TransitionBelief, Option<IntrinsicGoal>), ThoughtError> {
        let state_k = validate_clean_key(&transition.state_key, "state_key")?;
        let action_k = validate_clean_key(&transition.action_key, "action_key")?;
        let pred_k = validate_clean_key(&transition.predicted_next_key, "predicted_next_key")?;
        let obs_k = validate_clean_key(&transition.observed_next_key, "observed_next_key")?;

        let composite_key = format!("{state_k}::{action_k}");
        if !self.beliefs.contains_key(&composite_key)
            && self.beliefs.len() >= MAX_WORLD_TRANSITIONS
            && let Some(first_key) = self.beliefs.keys().next().cloned()
        {
            self.beliefs.remove(&first_key);
        }

        let mismatch = pred_k != obs_k;
        let entry = self
            .beliefs
            .entry(composite_key.clone())
            .or_insert_with(|| TransitionBelief {
                state_key: state_k.clone(),
                action_key: action_k.clone(),
                expected_outcome_key: obs_k.clone(),
                observations: 0,
                prediction_errors: 0,
                surprise_bps: 0,
                epistemic_uncertainty_bps: 10_000,
            });

        entry.observations = entry.observations.saturating_add(1);
        if mismatch {
            entry.prediction_errors = entry.prediction_errors.saturating_add(1);
            entry.expected_outcome_key.clone_from(&obs_k);
        }

        let err_ratio_bps = entry
            .prediction_errors
            .saturating_mul(10_000)
            .checked_div(entry.observations)
            .unwrap_or(0)
            .min(10_000);
        let instant_surprise = if mismatch { 8_500_u32 } else { 0_u32 };
        entry.surprise_bps = (err_ratio_bps / 2).saturating_add(instant_surprise / 2);

        let decay = entry.observations.saturating_mul(1_200).min(8_500);
        entry.epistemic_uncertainty_bps = 10_000_u32
            .saturating_sub(decay)
            .saturating_add(err_ratio_bps / 2)
            .min(10_000);

        let snapshot = entry.clone();

        let intrinsic_goal = if snapshot.surprise_bps >= SURPRISE_GOAL_THRESHOLD_BPS
            || snapshot.epistemic_uncertainty_bps >= 7_500
        {
            let info_gain = snapshot
                .surprise_bps
                .max(snapshot.epistemic_uncertainty_bps);
            Some(IntrinsicGoal {
                goal_id: format!("agi.goal.{state_k}.{action_k}"),
                target_state_key: state_k,
                target_action_key: action_k,
                directive_key: "i18n.agi.minimize_prediction_error_and_forge_shortcut".to_owned(),
                expected_information_gain_bps: info_gain,
                priority_bps: info_gain,
            })
        } else {
            None
        };

        Ok((snapshot, intrinsic_goal))
    }

    pub fn evaluate_godel_upgrade(
        &mut self,
        candidate: AlgorithmicStrategy,
    ) -> Result<GodelUpgradeVerdict, ThoughtError> {
        let domain_k = validate_clean_key(&candidate.domain_key, "domain_key")?;
        let strat_id = validate_clean_key(&candidate.strategy_id, "strategy_id")?;
        let digest = validate_clean_key(&candidate.proof_digest, "proof_digest")?;

        if !digest.starts_with("fnv64:") || candidate.code_complexity_bytes == 0 {
            return Err(ThoughtError::InvalidText {
                field: "proof_digest",
                reason: "requires valid deterministic proof digest and non-zero complexity",
            });
        }

        let Some(incumbent) = self.strategies.get(&domain_k) else {
            if self.strategies.len() >= MAX_STRATEGIES
                && let Some(first_k) = self.strategies.keys().next().cloned()
            {
                self.strategies.remove(&first_k);
            }
            let initial_gen = candidate.generation.max(1);
            let mut stored = candidate;
            stored.domain_key.clone_from(&domain_k);
            stored.strategy_id.clone_from(&strat_id);
            stored.generation = initial_gen;
            self.strategies.insert(domain_k.clone(), stored);
            return Ok(GodelUpgradeVerdict {
                domain_key: domain_k,
                upgraded: true,
                active_strategy_id: strat_id,
                active_generation: initial_gen,
                compression_gain_bps: 10_000,
                latency_gain_bps: 10_000,
                token_savings_bps: 10_000,
                reason_key: "i18n.agi.initial_strategy_installed".to_owned(),
            });
        };

        let accuracy_ok = candidate.success_rate_bps >= incumbent.success_rate_bps;
        let not_worse_latency = candidate.mean_latency_ms <= incumbent.mean_latency_ms;
        let not_worse_tokens = candidate.mean_token_cost <= incumbent.mean_token_cost;
        let strictly_better = candidate.success_rate_bps > incumbent.success_rate_bps
            || candidate.mean_latency_ms < incumbent.mean_latency_ms
            || candidate.mean_token_cost < incumbent.mean_token_cost
            || candidate.code_complexity_bytes < incumbent.code_complexity_bytes;

        let pareto_dominates =
            accuracy_ok && not_worse_latency && not_worse_tokens && strictly_better;

        if pareto_dominates {
            let latency_gain_bps =
                ratio_gain_bps(incumbent.mean_latency_ms, candidate.mean_latency_ms);
            let token_savings_bps =
                ratio_gain_bps(incumbent.mean_token_cost, candidate.mean_token_cost);
            let compression_gain_bps = ratio_gain_bps(
                u64::try_from(incumbent.code_complexity_bytes).unwrap_or(1),
                u64::try_from(candidate.code_complexity_bytes).unwrap_or(1),
            );
            let next_gen = incumbent.generation.saturating_add(1);
            let mut stored = candidate;
            stored.domain_key.clone_from(&domain_k);
            stored.strategy_id.clone_from(&strat_id);
            stored.generation = next_gen;
            self.strategies.insert(domain_k.clone(), stored);

            Ok(GodelUpgradeVerdict {
                domain_key: domain_k,
                upgraded: true,
                active_strategy_id: strat_id,
                active_generation: next_gen,
                compression_gain_bps,
                latency_gain_bps,
                token_savings_bps,
                reason_key: "i18n.agi.pareto_dominant_self_upgrade_applied".to_owned(),
            })
        } else {
            Ok(GodelUpgradeVerdict {
                domain_key: domain_k,
                upgraded: false,
                active_strategy_id: incumbent.strategy_id.clone(),
                active_generation: incumbent.generation,
                compression_gain_bps: 0,
                latency_gain_bps: 0,
                token_savings_bps: 0,
                reason_key: "i18n.agi.candidate_rejected_non_dominant".to_owned(),
            })
        }
    }

    #[must_use]
    pub fn active_strategy(&self, domain_key: &str) -> Option<&AlgorithmicStrategy> {
        self.strategies.get(domain_key)
    }
}
