use std::time::Duration;

use pyo3::{exceptions::PyRuntimeError, prelude::*};
use serde_json::{Value, json};

const ENDPOINT: &str = "https://api.typesafe.ai/v1/systemone";

fn accepts(answer: &Value) -> bool {
    let Some(route) = answer.pointer("/answers/route") else {
        return false;
    };
    route.get("type").and_then(Value::as_str) == Some("choice")
        && route.get("choice").and_then(Value::as_str) == Some("simple")
        && route
            .get("confidence")
            .and_then(Value::as_f64)
            .is_some_and(|confidence| (0.95..=1.0).contains(&confidence))
}

#[pyfunction]
fn jev_simple_windows_task(py: Python<'_>, text: String, key: String) -> PyResult<bool> {
    if text.is_empty() || text.len() > 768 || key.trim().is_empty() {
        return Ok(false);
    }
    py.detach(move || {
        let agent: ureq::Agent = ureq::Agent::config_builder()
            .https_only(true)
            .max_redirects(0)
            .timeout_global(Some(Duration::from_secs(2)))
            .build()
            .into();
        let payload = json!({
            "state": text,
            "model": "jev-latest",
            "questions": {"route": {
                "type": "choice",
                "instructions": "Classify the Windows request by the complexity of the action plan.",
                "criteria": {
                    "simple": "Exactly one explicit, read-only desktop operation, with a clear target and no external research.",
                    "deep": "Ambiguous, sensitive, state-changing, multi-step or otherwise complex request."
                }
            }}
        });
        let mut response = agent
            .post(ENDPOINT)
            .header("Authorization", format!("Bearer {key}"))
            .send_json(payload)
            .map_err(|_| PyRuntimeError::new_err("jev_transport_failed"))?;
        let answer: Value = response
            .body_mut()
            .with_config()
            .limit(16_384)
            .read_json()
            .map_err(|_| PyRuntimeError::new_err("jev_response_invalid"))?;
        Ok(accepts(&answer))
    })
}

pub(crate) fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(jev_simple_windows_task, module)?)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_only_high_confidence_simple_decisions() {
        for (choice, confidence, expected) in [
            ("simple", 0.95, true),
            ("simple", 0.94, false),
            ("simple", 1.01, false),
            ("deep", 0.99, false),
            ("unknown", 1.0, false),
        ] {
            assert_eq!(
                accepts(&json!({"answers": {"route": {
                    "type": "choice", "choice": choice, "confidence": confidence
                }}})),
                expected
            );
        }
        assert!(!accepts(&json!({})));
    }
}
