use agency_domain::Proof;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct GateVerdict {
    pub passed: bool,
    pub verified_proofs: usize,
    pub total_proofs: usize,
    pub missing_artifacts: Vec<String>,
    pub failing_commands: Vec<String>,
}

#[must_use]
pub fn evaluate_gate(
    proofs: &[Proof],
    required_artifacts: &[String],
    written_artifacts: &[String],
) -> GateVerdict {
    let mut verified_proofs: usize = 0;
    let mut failing_commands = Vec::new();

    for proof in proofs {
        if proof.is_verified() {
            verified_proofs = verified_proofs.saturating_add(1);
        } else {
            failing_commands.push(proof.command().as_str().to_owned());
        }
    }

    let mut missing_artifacts = Vec::new();
    for req in required_artifacts {
        if !written_artifacts.iter().any(|w| w == req) {
            missing_artifacts.push(req.clone());
        }
    }

    let passed = !proofs.is_empty() && failing_commands.is_empty() && missing_artifacts.is_empty();

    GateVerdict {
        passed,
        verified_proofs,
        total_proofs: proofs.len(),
        missing_artifacts,
        failing_commands,
    }
}
