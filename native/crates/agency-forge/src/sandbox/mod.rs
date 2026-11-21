use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::ForgeError;
use crate::manifest::ToolTestCase;
use crate::pipeline::values_equivalent;

pub const MAX_WALL_MS: u64 = 4_000;
pub const MAX_STDOUT_BYTES: usize = 65_536;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SandboxExecutionOutcome {
    pub case_index: usize,
    pub exit_code: i32,
    pub duration_ms: u64,
    pub stdout_json: Option<Value>,
    pub stderr_excerpt: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerificationProof {
    pub tool_name: String,
    pub version: u32,
    pub passed_cases: usize,
    pub total_duration_ms: u64,
    pub digest: String,
}

fn compute_proof_digest(name: &str, version: u32, code: &str, passed: usize) -> String {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for byte in name
        .as_bytes()
        .iter()
        .chain(code.as_bytes().iter())
        .chain(&version.to_le_bytes())
        .chain(&passed.to_le_bytes())
    {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0100_0000_01b3);
    }
    format!("fnv64:{hash:016x}")
}

pub fn verify_sandbox_outcomes(
    tool_name: &str,
    version: u32,
    code: &str,
    expected_cases: &[ToolTestCase],
    outcomes: &[SandboxExecutionOutcome],
) -> Result<VerificationProof, ForgeError> {
    if expected_cases.is_empty() || outcomes.len() != expected_cases.len() {
        return Err(ForgeError::InvalidTests(
            "sandbox outcome count does not match deterministic test suite".to_owned(),
        ));
    }

    let mut total_duration_ms: u64 = 0;

    for (idx, (expected, outcome)) in expected_cases.iter().zip(outcomes.iter()).enumerate() {
        if outcome.case_index != idx {
            return Err(ForgeError::InvalidTests(format!(
                "out-of-order test execution at case {idx}"
            )));
        }
        if outcome.exit_code != 0 {
            let err_msg = outcome
                .stderr_excerpt
                .as_deref()
                .unwrap_or("non-zero exit code");
            return Err(ForgeError::InvalidTests(format!(
                "case {idx} exited with code {}: {err_msg}",
                outcome.exit_code
            )));
        }
        if outcome.duration_ms > MAX_WALL_MS {
            return Err(ForgeError::InvalidTests(format!(
                "case {idx} exceeded sandbox wall time ({}ms > {MAX_WALL_MS}ms)",
                outcome.duration_ms
            )));
        }
        let Some(actual) = &outcome.stdout_json else {
            return Err(ForgeError::InvalidTests(format!(
                "case {idx} produced no valid JSON output"
            )));
        };
        if !values_equivalent(actual, &expected.expect) {
            return Err(ForgeError::InvalidTests(format!(
                "case {idx} output mismatch against expected deterministic value"
            )));
        }
        total_duration_ms = total_duration_ms.saturating_add(outcome.duration_ms);
    }

    let passed_cases = expected_cases.len();
    let digest = compute_proof_digest(tool_name, version, code, passed_cases);

    Ok(VerificationProof {
        tool_name: tool_name.to_owned(),
        version,
        passed_cases,
        total_duration_ms,
        digest,
    })
}
