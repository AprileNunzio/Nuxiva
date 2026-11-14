use nuxiva_llm_core::{
    Candidate, CriticWeights, Group, PrivacyDetector, Verdict, best_index, cosine, group_models,
    retrieve, round3, score, valid_text,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const MAX_MODELS: usize = 256;
const MAX_AGENTS: usize = 4096;
const MAX_DIMENSIONS: usize = 16_384;
const MAX_CANDIDATES: usize = 64;

fn rank_error(error: &nuxiva_llm_core::RankError) -> PyErr {
    PyValueError::new_err(error.to_string())
}

#[pyfunction]
fn llm_valid_text(text: &str) -> bool {
    valid_text(text)
}

#[pyfunction]
#[pyo3(signature = (confidence, critic, confidence_weight, critic_weight))]
fn llm_score(
    confidence: f64,
    critic: Option<f64>,
    confidence_weight: f64,
    critic_weight: f64,
) -> PyResult<f64> {
    if !confidence.is_finite() || critic.is_some_and(|value| !value.is_finite()) {
        return Err(PyValueError::new_err("llm.score.not_finite"));
    }
    let weights = CriticWeights {
        confidence: confidence_weight,
        critic: critic_weight,
    };
    Ok(round3(score(confidence, critic, weights)))
}

#[pyfunction]
fn llm_best_index(scores: Vec<f64>) -> PyResult<Option<usize>> {
    if scores.len() > MAX_CANDIDATES || scores.iter().any(|value| value.is_nan()) {
        return Err(PyValueError::new_err("llm.best.invalid"));
    }
    let candidates: Vec<Candidate> = scores
        .into_iter()
        .map(|score| Candidate {
            has_text: true,
            score,
        })
        .collect();
    Ok(best_index(&candidates))
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn llm_group_models(models: Vec<(String, bool)>) -> PyResult<Vec<(String, Vec<String>)>> {
    if models.len() > MAX_MODELS {
        return Err(PyValueError::new_err("llm.models.too_many"));
    }
    Ok(group_models(&models)
        .into_iter()
        .map(|group| match group {
            Group::Cloud(name) => ("cloud".to_owned(), vec![name]),
            Group::Local(names) => ("local".to_owned(), names),
        })
        .collect())
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn llm_retrieve(
    py: Python<'_>,
    prompt: Vec<f64>,
    indexed: Vec<(String, Vec<f64>)>,
    top_k: usize,
    always: Vec<String>,
) -> PyResult<Vec<String>> {
    let oversized = prompt.len() > MAX_DIMENSIONS
        || indexed.len() > MAX_AGENTS
        || indexed
            .iter()
            .any(|(_, vector)| vector.len() > MAX_DIMENSIONS);
    if oversized {
        return Err(PyValueError::new_err("llm.retrieve.too_large"));
    }
    let core: Vec<&str> = always.iter().map(String::as_str).collect();
    py.detach(|| retrieve(&prompt, &indexed, top_k, &core))
        .map(|chosen| chosen.into_iter().collect())
        .map_err(|error| rank_error(&error))
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn llm_cosine(left: Vec<f64>, right: Vec<f64>) -> PyResult<f64> {
    if left.len() > MAX_DIMENSIONS || right.len() > MAX_DIMENSIONS {
        return Err(PyValueError::new_err("llm.cosine.too_large"));
    }
    cosine(&left, &right).map_err(|error| rank_error(&error))
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustPrivacy {
    detector: PrivacyDetector,
}

#[pymethods]
impl RustPrivacy {
    #[new]
    fn new() -> PyResult<Self> {
        PrivacyDetector::new()
            .map(|detector| Self { detector })
            .map_err(|error| PyValueError::new_err(error.to_string()))
    }

    #[allow(clippy::needless_pass_by_value)]
    fn classify_all(
        &self,
        py: Python<'_>,
        texts: Vec<String>,
        names: Vec<String>,
    ) -> PyResult<(&'static str, &'static str)> {
        if texts.len() > MAX_CANDIDATES {
            return Ok(("defer", ""));
        }
        py.detach(|| self.detector.classify_all(&texts, &names))
            .map(|verdict| match verdict {
                Verdict::Level(level) => ("level", level.name()),
                Verdict::Defer => ("defer", ""),
            })
            .map_err(|error| PyValueError::new_err(error.to_string()))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustPrivacy>()?;
    m.add_function(wrap_pyfunction!(llm_valid_text, m)?)?;
    m.add_function(wrap_pyfunction!(llm_score, m)?)?;
    m.add_function(wrap_pyfunction!(llm_best_index, m)?)?;
    m.add_function(wrap_pyfunction!(llm_group_models, m)?)?;
    m.add_function(wrap_pyfunction!(llm_retrieve, m)?)?;
    m.add_function(wrap_pyfunction!(llm_cosine, m)?)
}
