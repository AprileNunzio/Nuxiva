use serde::{Deserialize, Serialize};

use crate::error::ThoughtError;

pub const MAX_CANDIDATES: usize = 32;
const MAX_ID_LEN: usize = 64;
const MAX_TITLE_LEN: usize = 200;
const MAX_SUMMARY_LEN: usize = 2_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct EvaluationWeights {
    pub scalability_bps: u32,
    pub security_bps: u32,
    pub maintainability_bps: u32,
    pub velocity_bps: u32,
    pub cost_efficiency_bps: u32,
}

impl Default for EvaluationWeights {
    fn default() -> Self {
        Self {
            scalability_bps: 2_500,
            security_bps: 2_500,
            maintainability_bps: 2_000,
            velocity_bps: 1_500,
            cost_efficiency_bps: 1_500,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ArchitectureCandidate {
    pub id: String,
    pub title: String,
    pub summary: String,
    pub stack: Vec<String>,
    pub scalability: u8,
    pub security: u8,
    pub maintainability: u8,
    pub velocity: u8,
    pub cost_efficiency: u8,
    pub risk_penalty: u8,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RankedBranch {
    pub id: String,
    pub title: String,
    pub score_bps: u32,
    pub strengths: Vec<String>,
    pub risks: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ThoughtVerdict {
    pub selected_id: String,
    pub selected_title: String,
    pub selected_score_bps: u32,
    pub rationale: String,
    pub required_specialists: Vec<String>,
    pub branches: Vec<RankedBranch>,
}

fn validate_candidate(c: &ArchitectureCandidate) -> Result<(), ThoughtError> {
    let trimmed = c.id.trim();
    if trimmed.is_empty() || trimmed.len() > MAX_ID_LEN {
        return Err(ThoughtError::InvalidIdentifier(c.id.clone()));
    }
    if c.title.trim().is_empty() || c.title.len() > MAX_TITLE_LEN {
        return Err(ThoughtError::InvalidText {
            field: "title",
            reason: "must be non-empty and within length limit",
        });
    }
    if c.summary.len() > MAX_SUMMARY_LEN {
        return Err(ThoughtError::InvalidText {
            field: "summary",
            reason: "exceeds maximum length",
        });
    }
    Ok(())
}

fn clamp_metric(val: u8) -> u32 {
    u32::from(val.min(100))
}

fn compute_score(c: &ArchitectureCandidate, w: EvaluationWeights) -> u32 {
    let s1 = clamp_metric(c.scalability).saturating_mul(w.scalability_bps);
    let s2 = clamp_metric(c.security).saturating_mul(w.security_bps);
    let s3 = clamp_metric(c.maintainability).saturating_mul(w.maintainability_bps);
    let s4 = clamp_metric(c.velocity).saturating_mul(w.velocity_bps);
    let s5 = clamp_metric(c.cost_efficiency).saturating_mul(w.cost_efficiency_bps);
    let weighted = s1
        .saturating_add(s2)
        .saturating_add(s3)
        .saturating_add(s4)
        .saturating_add(s5)
        .checked_div(100)
        .unwrap_or(0);
    let penalty = clamp_metric(c.risk_penalty).saturating_mul(150);
    weighted.saturating_sub(penalty)
}

fn extract_strengths(c: &ArchitectureCandidate) -> Vec<String> {
    let mut out = Vec::new();
    if c.scalability >= 80 {
        out.push("alta scalabilita orizzontale".to_owned());
    }
    if c.security >= 80 {
        out.push("isolamento zero-trust e sicurezza".to_owned());
    }
    if c.maintainability >= 80 {
        out.push("modularita clean architecture".to_owned());
    }
    if c.velocity >= 80 {
        out.push("rapida iterazione e consegna".to_owned());
    }
    if c.cost_efficiency >= 80 {
        out.push("efficienza risorse e budget".to_owned());
    }
    out
}

fn extract_risks(c: &ArchitectureCandidate) -> Vec<String> {
    let mut out = Vec::new();
    if c.security < 60 {
        out.push("superficie di attacco da mitigare".to_owned());
    }
    if c.scalability < 60 {
        out.push("potenziale collo di bottiglia sotto carico".to_owned());
    }
    if c.maintainability < 60 {
        out.push("accoppiamento tecnico elevato".to_owned());
    }
    if c.risk_penalty >= 30 {
        out.push("rischio operativo significativo".to_owned());
    }
    out
}

fn infer_specialists_from_stack(stack: &[String]) -> Vec<String> {
    let mut roles = vec!["architect".to_owned()];
    for item in stack {
        let lower = item.to_lowercase();
        if (lower.contains("rust")
            || lower.contains("api")
            || lower.contains("postgres")
            || lower.contains("sql")
            || lower.contains("fastapi")
            || lower.contains("tokio"))
            && !roles.iter().any(|r| r == "backend")
        {
            roles.push("backend".to_owned());
        }
        if (lower.contains("react")
            || lower.contains("svelte")
            || lower.contains("ui")
            || lower.contains("web")
            || lower.contains("css")
            || lower.contains("three"))
            && !roles.iter().any(|r| r == "frontend")
        {
            roles.push("frontend".to_owned());
        }
        if (lower.contains("stripe")
            || lower.contains("auth")
            || lower.contains("zero-trust")
            || lower.contains("tls")
            || lower.contains("vault"))
            && !roles.iter().any(|r| r == "security")
        {
            roles.push("security".to_owned());
        }
        if (lower.contains("docker") || lower.contains("systemd") || lower.contains("ci"))
            && !roles.iter().any(|r| r == "devops")
        {
            roles.push("devops".to_owned());
        }
    }
    if !roles.iter().any(|r| r == "qa") {
        roles.push("qa".to_owned());
    }
    roles
}

pub fn evaluate_candidates(
    candidates: &[ArchitectureCandidate],
    weights: EvaluationWeights,
) -> Result<ThoughtVerdict, ThoughtError> {
    if candidates.is_empty() {
        return Err(ThoughtError::EmptyCandidates);
    }
    if candidates.len() > MAX_CANDIDATES {
        return Err(ThoughtError::TooManyCandidates(MAX_CANDIDATES));
    }
    for candidate in candidates {
        validate_candidate(candidate)?;
    }

    let mut branches: Vec<(RankedBranch, &ArchitectureCandidate)> = candidates
        .iter()
        .map(|c| {
            let branch = RankedBranch {
                id: c.id.trim().to_owned(),
                title: c.title.trim().to_owned(),
                score_bps: compute_score(c, weights),
                strengths: extract_strengths(c),
                risks: extract_risks(c),
            };
            (branch, c)
        })
        .collect();

    branches.sort_by(|a, b| {
        b.0.score_bps
            .cmp(&a.0.score_bps)
            .then_with(|| a.0.id.cmp(&b.0.id))
    });

    let Some((winner_branch, winner_cand)) = branches.first() else {
        return Err(ThoughtError::EmptyCandidates);
    };

    let selected_id = winner_branch.id.clone();
    let selected_title = winner_branch.title.clone();
    let selected_score_bps = winner_branch.score_bps;
    let required_specialists = infer_specialists_from_stack(&winner_cand.stack);
    let strengths_summary = if winner_branch.strengths.is_empty() {
        "bilanciamento generale ottimale".to_owned()
    } else {
        winner_branch.strengths.join(", ")
    };
    let rationale = format!(
        "Soluzione selezionata '{selected_title}' (punteggio {selected_score_bps} bps) per: {strengths_summary}."
    );

    let ranked_branches = branches.into_iter().map(|(b, _)| b).collect();

    Ok(ThoughtVerdict {
        selected_id,
        selected_title,
        selected_score_bps,
        rationale,
        required_specialists,
        branches: ranked_branches,
    })
}
