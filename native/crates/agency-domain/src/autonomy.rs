use serde::{Deserialize, Serialize};

use crate::error::DomainError;
use crate::text::CleanText;

const MAX_RATIONALE: usize = 500;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[allow(clippy::struct_excessive_bools)]
pub struct AutonomyDecision {
    approved: bool,
    risk: RiskLevel,
    confidence: f64,
    reversible: bool,
    requires_double_permission: bool,
    autonomous: bool,
    rationale: CleanText,
}

impl AutonomyDecision {
    #[must_use]
    pub fn is_approved(&self) -> bool {
        self.approved
    }

    #[must_use]
    pub fn risk(&self) -> RiskLevel {
        self.risk
    }

    #[must_use]
    pub fn confidence(&self) -> f64 {
        self.confidence
    }

    #[must_use]
    pub fn is_reversible(&self) -> bool {
        self.reversible
    }

    #[must_use]
    pub fn requires_double_permission(&self) -> bool {
        self.requires_double_permission
    }

    #[must_use]
    pub fn is_autonomous(&self) -> bool {
        self.autonomous
    }

    #[must_use]
    pub fn rationale(&self) -> &CleanText {
        &self.rationale
    }
}

fn contains_word(haystack: &str, word: &str) -> bool {
    haystack
        .split(|c: char| !c.is_alphanumeric() && c != '_')
        .any(|w| w.eq_ignore_ascii_case(word))
}

#[must_use]
pub fn classify_risk(title: &str, role: &str, criteria: &[&str]) -> RiskLevel {
    let mut combined = String::new();
    combined.push_str(title);
    combined.push(' ');
    combined.push_str(role);
    for c in criteria {
        combined.push(' ');
        combined.push_str(c);
    }

    for needle in [
        "password",
        "passwd",
        "secret",
        "api_key",
        "token",
        "credential",
        "private_key",
        "iban",
        "conto",
        "cvv",
        "sudo",
        "format",
        "chmod",
    ] {
        if contains_word(&combined, needle) {
            return RiskLevel::Critical;
        }
    }

    for needle in [
        "delete",
        "remove",
        "truncate",
        "unlink",
        "purge",
        "migration",
        "schema",
        "deploy",
        "production",
        "payment",
        "stripe",
        "checkout",
    ] {
        if contains_word(&combined, needle) {
            return RiskLevel::High;
        }
    }

    for needle in [
        "endpoint",
        "route",
        "controller",
        "handler",
        "service",
        "query",
        "write_file",
        "patch",
        "refactor",
        "update",
    ] {
        if contains_word(&combined, needle) {
            return RiskLevel::Medium;
        }
    }

    RiskLevel::Low
}

#[must_use]
#[allow(clippy::cast_precision_loss)]
pub fn compute_confidence(
    status: Option<&str>,
    proofs_total: usize,
    proofs_verified: usize,
    critic_approved: Option<bool>,
) -> f64 {
    if matches!(status, Some("done")) {
        return 0.98;
    }

    let base = if proofs_total == 0 {
        if critic_approved.is_none() {
            0.85
        } else {
            0.88
        }
    } else {
        let ratio = proofs_verified as f64 / proofs_total.max(1) as f64;
        0.70 + (0.28 * ratio)
    };

    let score = match critic_approved {
        Some(true) => (base + 0.08).min(0.99),
        Some(false) => (base - 0.35).max(0.40),
        None => base,
    };

    (score * 1000.0).round() / 1000.0
}

pub fn evaluate_task(
    title: &str,
    role: &str,
    criteria: &[&str],
    status: Option<&str>,
    proofs_total: usize,
    proofs_verified: usize,
    critic_approved: Option<bool>,
) -> Result<AutonomyDecision, DomainError> {
    let risk = classify_risk(title, role, criteria);
    let confidence = compute_confidence(status, proofs_total, proofs_verified, critic_approved);
    let reversible =
        risk != RiskLevel::Critical && !title.to_ascii_lowercase().contains("irreversible");
    let requires_double_permission = risk == RiskLevel::Critical;

    let (approved, autonomous, message) = if (risk == RiskLevel::Low || risk == RiskLevel::Medium)
        && confidence >= 0.94
        && reversible
        && critic_approved != Some(false)
    {
        (
            true,
            true,
            format!(
                "CEO autonomo: approvato per rischio {risk:?} e confidenza {:.0}%",
                confidence * 100.0
            ),
        )
    } else if risk == RiskLevel::Critical {
        (
            false,
            false,
            "Blocco di sicurezza: azione critica richiedente doppio permesso umano".to_string(),
        )
    } else if risk == RiskLevel::High {
        (
            false,
            false,
            format!(
                "Revisione umana richiesta: rischio {risk:?} con confidenza {:.0}%",
                confidence * 100.0
            ),
        )
    } else {
        (
            false,
            false,
            format!(
                "In attesa di verifica: confidenza {:.0}% insufficiente",
                confidence * 100.0
            ),
        )
    };

    Ok(AutonomyDecision {
        approved,
        risk,
        confidence,
        reversible,
        requires_double_permission,
        autonomous,
        rationale: CleanText::new("rationale", &message, MAX_RATIONALE)?,
    })
}
