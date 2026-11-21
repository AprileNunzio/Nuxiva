use serde::{Deserialize, Serialize};

use crate::error::ThoughtError;
use crate::socratic::{
    DialecticExchange, InquiryScope, ResolutionSource, SocraticReport, classify_resolution,
    compute_voi_bps,
};

const MAX_HYPOTHESES: usize = 32;
const MAX_PROBE_LEN: usize = 300;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProbeChannel {
    Filesystem,
    CodeIndex,
    NetworkDiscovery,
    MemoryGraph,
    EnvironmentConfig,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EpistemicHypothesis {
    pub id: String,
    pub scope: InquiryScope,
    pub question_key: String,
    pub default_answer_key: String,
    pub impact_on_schema: u8,
    pub reversibility: u8,
    pub probe_channel: Option<ProbeChannel>,
    pub probe_query: Option<String>,
    pub options_keys: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProbeFinding {
    pub hypothesis_id: String,
    pub resolved: bool,
    pub resolved_answer_key: String,
    pub confidence_boost_bps: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EpistemicPlan {
    pub goal: String,
    pub self_probes: Vec<EpistemicHypothesis>,
    pub report: SocraticReport,
}

fn sanitize_token(raw: &str, field: &'static str, max_len: usize) -> Result<String, ThoughtError> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err(ThoughtError::InvalidText {
            field,
            reason: "must not be empty",
        });
    }
    if trimmed.len() > max_len {
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

pub fn synthesize_epistemic_plan(
    goal: &str,
    hypotheses: &[EpistemicHypothesis],
    findings: &[ProbeFinding],
    has_shared_contracts: &[String],
) -> Result<EpistemicPlan, ThoughtError> {
    let clean_goal = sanitize_token(goal, "goal", 1_200)?;
    if hypotheses.len() > MAX_HYPOTHESES {
        return Err(ThoughtError::TooManyCandidates(MAX_HYPOTHESES));
    }

    let mut self_probes = Vec::new();
    let mut autonomous_decisions = Vec::new();
    let mut user_escalations = Vec::new();
    let mut total_boost_bps: u32 = 0;

    for hyp in hypotheses {
        let clean_id = sanitize_token(&hyp.id, "id", 120)?;
        let clean_q = sanitize_token(&hyp.question_key, "question_key", 600)?;
        let clean_ans = sanitize_token(&hyp.default_answer_key, "default_answer_key", 1_200)?;
        if let Some(pq) = &hyp.probe_query {
            let _ = sanitize_token(pq, "probe_query", MAX_PROBE_LEN)?;
        }

        let matched_finding = findings
            .iter()
            .find(|f| f.hypothesis_id == clean_id && f.resolved);

        let goal_resolved = matched_finding.is_some();
        let voi_bps = compute_voi_bps(
            hyp.scope,
            hyp.impact_on_schema,
            hyp.reversibility,
            goal_resolved,
        );
        let has_contract = has_shared_contracts.iter().any(|c| c == &clean_id);
        let resolution = if goal_resolved {
            ResolutionSource::AutonomousArchitect
        } else {
            classify_resolution(voi_bps, has_contract)
        };

        if !goal_resolved && hyp.probe_channel.is_some() {
            self_probes.push(hyp.clone());
        }

        let final_answer = match matched_finding {
            Some(finding) => {
                total_boost_bps = total_boost_bps.saturating_add(finding.confidence_boost_bps);
                sanitize_token(&finding.resolved_answer_key, "resolved_answer_key", 1_200)?
            }
            None => clean_ans,
        };

        let mut clean_options = Vec::with_capacity(hyp.options_keys.len());
        for opt in &hyp.options_keys {
            clean_options.push(sanitize_token(opt, "option_key", 300)?);
        }

        let exchange = DialecticExchange {
            id: clean_id,
            scope: hyp.scope,
            question: clean_q,
            answer: final_answer,
            resolution,
            voi_bps,
            options: clean_options,
        };

        if resolution == ResolutionSource::EscalateToUser {
            user_escalations.push(exchange);
        } else {
            autonomous_decisions.push(exchange);
        }
    }

    let penalty = u32::try_from(user_escalations.len())
        .unwrap_or(10)
        .saturating_mul(1_100);
    let base_confidence = 9_200_u32
        .saturating_add(total_boost_bps.min(800))
        .min(9_900);
    let confidence_bps = base_confidence.saturating_sub(penalty).max(5_000);

    let invariants = vec![
        "i18n.invariant.zero_trust_boundaries".to_owned(),
        "i18n.invariant.modular_under_500_lines".to_owned(),
        "i18n.invariant.atomic_persistence_verifiable_proofs".to_owned(),
    ];

    Ok(EpistemicPlan {
        goal: clean_goal.clone(),
        self_probes,
        report: SocraticReport {
            goal: clean_goal,
            autonomous_decisions,
            user_escalations,
            invariants,
            confidence_bps,
        },
    })
}
