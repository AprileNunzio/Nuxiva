use nuxiva_config_core::{
    apply_plan, is_secret, normalize_ollama, ollama_remote, ollama_url, parse_env, reload_units,
    rewrite_env, valid_key,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const MAX_TEXT: usize = 4 << 20;
const MAX_ITEMS: usize = 4096;

fn bounded(text: &str) -> PyResult<&str> {
    if text.len() > MAX_TEXT {
        return Err(PyValueError::new_err("config.input.too_large"));
    }
    Ok(text)
}

fn counted<T>(items: &[T]) -> PyResult<()> {
    if items.len() > MAX_ITEMS {
        return Err(PyValueError::new_err("config.input.too_large"));
    }
    Ok(())
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustSecretPolicy {
    explicit: Vec<String>,
}

#[pymethods]
impl RustSecretPolicy {
    #[new]
    fn new(explicit: Vec<String>) -> PyResult<Self> {
        counted(&explicit)?;
        Ok(Self { explicit })
    }

    fn is_secret(&self, key: &str) -> bool {
        let explicit: Vec<&str> = self.explicit.iter().map(String::as_str).collect();
        is_secret(key, &explicit)
    }
}

#[pyfunction]
fn config_valid_key(key: &str) -> bool {
    valid_key(key)
}

#[pyfunction]
fn config_parse_env(text: &str) -> PyResult<Vec<(String, String)>> {
    Ok(parse_env(bounded(text)?))
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn config_rewrite_env(text: &str, updates: Vec<(String, String)>) -> PyResult<String> {
    counted(&updates)?;
    rewrite_env(bounded(text)?, &updates)
        .map_err(|e| PyValueError::new_err(format!("Chiave o valore non valido: {}", e.key())))
}

#[pyfunction]
fn config_ollama_url(custom: &str, default: &str) -> String {
    ollama_url(custom, default)
}

#[pyfunction]
fn config_normalize_ollama(value: &str) -> Option<String> {
    normalize_ollama(value)
}

#[pyfunction]
fn config_ollama_remote(url: &str) -> bool {
    ollama_remote(url)
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn config_apply_plan(
    keys: Vec<String>,
    extra: Vec<String>,
    known: Vec<String>,
) -> PyResult<Vec<String>> {
    counted(&keys)?;
    counted(&extra)?;
    counted(&known)?;
    Ok(apply_plan(&keys, &extra, &known))
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn config_reload_units(keys: Vec<String>) -> PyResult<Vec<String>> {
    counted(&keys)?;
    Ok(reload_units(&keys))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustSecretPolicy>()?;
    m.add_function(wrap_pyfunction!(config_valid_key, m)?)?;
    m.add_function(wrap_pyfunction!(config_parse_env, m)?)?;
    m.add_function(wrap_pyfunction!(config_rewrite_env, m)?)?;
    m.add_function(wrap_pyfunction!(config_ollama_url, m)?)?;
    m.add_function(wrap_pyfunction!(config_normalize_ollama, m)?)?;
    m.add_function(wrap_pyfunction!(config_ollama_remote, m)?)?;
    m.add_function(wrap_pyfunction!(config_apply_plan, m)?)?;
    m.add_function(wrap_pyfunction!(config_reload_units, m)?)?;
    Ok(())
}
