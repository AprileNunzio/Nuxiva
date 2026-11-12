use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::ast_guard::ALLOWED_IMPORTS;
use crate::error::ForgeError;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SynthesisDiagnosis {
    pub recoverable: bool,
    pub category: &'static str,
    pub hint: String,
    pub allowed_imports: Vec<String>,
}

#[must_use]
pub fn diagnose_failure(error: &ForgeError) -> SynthesisDiagnosis {
    let allowed_imports = ALLOWED_IMPORTS.iter().map(|s| (*s).to_owned()).collect();
    match error {
        ForgeError::InvalidName(name) => SynthesisDiagnosis {
            recoverable: true,
            category: "naming",
            hint: format!(
                "Usa un identificatore snake_case valido (3..=40 caratteri) invece di '{name}'."
            ),
            allowed_imports,
        },
        ForgeError::GuardRejected(reason) => SynthesisDiagnosis {
            recoverable: true,
            category: "security_guard",
            hint: format!(
                "Correggi il codice sorgente: {reason}. Esponi 'def run(args):' puro usando solo gli import consentiti."
            ),
            allowed_imports,
        },
        ForgeError::InvalidTests(reason) => SynthesisDiagnosis {
            recoverable: true,
            category: "test_suite",
            hint: format!(
                "Fornisci test deterministici validi ({reason}) con input ed 'expect' esatti."
            ),
            allowed_imports,
        },
        ForgeError::AlreadyExists(_)
        | ForgeError::NotFound(_)
        | ForgeError::NotCallable(_)
        | ForgeError::CapacityReached(_) => SynthesisDiagnosis {
            recoverable: false,
            category: "catalog_state",
            hint: error.to_string(),
            allowed_imports,
        },
    }
}

#[must_use]
pub fn values_equivalent(actual: &Value, expected: &Value) -> bool {
    match (actual, expected) {
        (Value::Number(a), Value::Number(b)) => {
            if let (Some(fa), Some(fb)) = (a.as_f64(), b.as_f64()) {
                (fa - fb).abs() <= 1e-9_f64.max(1e-9_f64 * fa.abs().max(fb.abs()))
            } else {
                a == b
            }
        }
        (Value::Array(a), Value::Array(b)) => {
            a.len() == b.len() && a.iter().zip(b.iter()).all(|(x, y)| values_equivalent(x, y))
        }
        (Value::Object(a), Value::Object(b)) => {
            a.len() == b.len()
                && a.iter()
                    .all(|(k, vx)| b.get(k).is_some_and(|vy| values_equivalent(vx, vy)))
        }
        _ => actual == expected,
    }
}
