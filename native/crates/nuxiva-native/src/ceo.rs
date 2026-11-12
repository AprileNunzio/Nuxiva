use crate::errors::poisoned;
use nuxiva_agent_core::ceo::{self, Card, Index, Learned, words};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::sync::RwLock;

const MAX_PAYLOAD: usize = 16 * 1024 * 1024;
const MAX_LEARNED: usize = 4 * 1024 * 1024;

fn json<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

fn parse<T: serde::de::DeserializeOwned>(raw: &str, limit: usize) -> PyResult<T> {
    if raw.len() > limit {
        return Err(PyValueError::new_err("payload too large"));
    }
    serde_json::from_str(raw).map_err(|e| PyValueError::new_err(e.to_string()))
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustCeoIndex {
    index: Index,
    learned: RwLock<Learned>,
}

#[pymethods]
impl RustCeoIndex {
    #[new]
    fn new(py: Python<'_>, cards_json: &str) -> PyResult<Self> {
        let cards: Vec<Card> = parse(cards_json, MAX_PAYLOAD)?;
        Ok(Self {
            index: py.detach(|| Index::new(cards)),
            learned: RwLock::new(Learned::new()),
        })
    }

    fn __len__(&self) -> usize {
        self.index.len()
    }

    fn set_learned(&self, learned_json: &str) -> PyResult<()> {
        let table: Learned = parse(learned_json, MAX_LEARNED)?;
        *self.learned.write().map_err(|_| poisoned())? = table;
        Ok(())
    }

    fn decide(&self, py: Python<'_>, text: &str) -> PyResult<String> {
        let learned = self.learned.read().map_err(|_| poisoned())?;
        let decision = py.detach(|| ceo::decide(&self.index, text, &learned));
        json(&decision)
    }

    fn rank(&self, py: Python<'_>, text: &str) -> PyResult<String> {
        let learned = self.learned.read().map_err(|_| poisoned())?;
        let ranked = py.detach(|| self.index.rank(text, &learned));
        json(&ranked)
    }

    fn invalid_phrases(&self) -> Vec<(String, String)> {
        self.index.invalid_phrases()
    }
}

#[pyfunction]
pub fn ceo_clean_tokens(text: &str) -> Vec<String> {
    words::clean_tokens(words::clip(text)).into_iter().collect()
}

#[pyfunction]
pub fn ceo_is_conversational(text: &str) -> bool {
    words::is_conversational(words::clip(text))
}

#[pyfunction]
pub fn ceo_lexicon() -> (Vec<String>, Vec<String>) {
    let split = |s: &str| s.split_whitespace().map(str::to_owned).collect();
    (split(ceo::lexicon::STOPWORDS), split(ceo::lexicon::GENERIC))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustCeoIndex>()?;
    m.add_function(wrap_pyfunction!(ceo_clean_tokens, m)?)?;
    m.add_function(wrap_pyfunction!(ceo_is_conversational, m)?)?;
    m.add_function(wrap_pyfunction!(ceo_lexicon, m)?)?;
    Ok(())
}
