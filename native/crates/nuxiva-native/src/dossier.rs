use nuxiva_dossier_core::doc::{self, Doc, Problem};
use nuxiva_dossier_core::kind::{self, Kind, Level};
use nuxiva_dossier_core::turn::{self, Contract, Input};
use nuxiva_dossier_core::{Store, StoreError, redact};
use pyo3::exceptions::{PyOSError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::path::Path;

const MAX_JSON: usize = 512 * 1024;

fn json<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

fn parse<T: serde::de::DeserializeOwned>(raw: &str) -> PyResult<T> {
    if raw.len() > MAX_JSON {
        return Err(PyValueError::new_err("payload too large"));
    }
    serde_json::from_str(raw).map_err(|e| PyValueError::new_err(e.to_string()))
}

fn store_error(e: StoreError) -> PyErr {
    match e {
        StoreError::Invalid(problems) => {
            PyValueError::new_err(json(&problems).unwrap_or_else(|_| "invalid".to_owned()))
        }
        StoreError::Path(why) => PyValueError::new_err(why),
        StoreError::Ledger(why) => PyRuntimeError::new_err(why),
        StoreError::Io(err) => PyOSError::new_err(err.to_string()),
    }
}

fn level(text: &str) -> PyResult<Level> {
    Level::parse(text).ok_or_else(|| PyValueError::new_err("unknown level"))
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustDossierStore {
    inner: Store,
}

#[pymethods]
impl RustDossierStore {
    #[new]
    fn new(root: &str, key: &[u8]) -> PyResult<Self> {
        let key: [u8; 32] = key
            .try_into()
            .map_err(|_| PyValueError::new_err("key must be 32 bytes"))?;
        Ok(Self {
            inner: Store::new(Path::new(root), key).map_err(store_error)?,
        })
    }

    fn open(&self, py: Python<'_>, level_name: &str, now_ms: u64) -> PyResult<String> {
        let level = level(level_name)?;
        py.detach(|| self.inner.open(now_ms, level))
            .map_err(store_error)
    }

    fn write(
        &self,
        py: Python<'_>,
        rel: &str,
        name: &str,
        doc_json: &str,
        now_ms: u64,
    ) -> PyResult<String> {
        let document: Doc = parse(doc_json)?;
        py.detach(|| self.inner.write(rel, name, &document, now_ms))
            .map_err(store_error)
    }

    fn read(&self, rel: &str, name: &str) -> PyResult<String> {
        json(&self.inner.read(rel, name).map_err(store_error)?)
    }

    fn verify(&self, py: Python<'_>, rel: &str) -> PyResult<String> {
        json(&py.detach(|| self.inner.verify(rel)).map_err(store_error)?)
    }

    fn expired(
        &self,
        py: Python<'_>,
        now_ms: u64,
        days: u64,
        limit: usize,
    ) -> PyResult<Vec<String>> {
        py.detach(|| self.inner.expired(now_ms, days, limit.min(10_000)))
            .map_err(store_error)
    }

    fn prune(&self, py: Python<'_>, rel: &str, now_ms: u64) -> PyResult<usize> {
        py.detach(|| self.inner.prune(rel, now_ms))
            .map_err(store_error)
    }
}

#[pyfunction]
pub fn dossier_render(doc_json: &str) -> PyResult<String> {
    Ok(doc::render(&parse::<Doc>(doc_json)?))
}

#[pyfunction]
pub fn dossier_parse(text: &str) -> PyResult<String> {
    match doc::parse(text) {
        Ok(d) => json(&d),
        Err(p) => Err(PyValueError::new_err(json(&vec![p])?)),
    }
}

#[pyfunction]
pub fn dossier_validate(doc_json: &str, kind_name: &str) -> PyResult<String> {
    let kind = Kind::parse(kind_name).ok_or_else(|| PyValueError::new_err("unknown kind"))?;
    json(&doc::validate(
        &doc::sanitize(&parse::<Doc>(doc_json)?),
        kind,
    ))
}

#[pyfunction]
pub fn dossier_redact(text: &str) -> PyResult<String> {
    if text.len() > MAX_JSON {
        return Err(PyValueError::new_err("text too large"));
    }
    Ok(redact::redact(text))
}

#[pyfunction]
pub fn dossier_patterns() -> (Vec<&'static str>, Vec<&'static str>, &'static str) {
    redact::patterns()
}

#[pyfunction]
pub fn dossier_step_file(number: u8, slug: &str) -> Option<String> {
    kind::step_file(number, slug)
}

#[pyfunction]
pub fn dossier_prompt(contract_json: &str, inputs_json: &str, nonce: &str) -> PyResult<String> {
    if nonce.len() < 16 || !nonce.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(PyValueError::new_err(
            "nonce must be at least 16 hex characters",
        ));
    }
    let contract: Contract = parse(contract_json)?;
    let inputs: Vec<Input> = parse(inputs_json)?;
    json(&turn::prompt(&contract, &inputs, nonce))
}

#[pyfunction]
pub fn dossier_check(contract_json: &str, reply: &str) -> PyResult<String> {
    let contract: Contract = parse(contract_json)?;
    json(&turn::check(&contract, reply))
}

#[pyfunction]
pub fn dossier_repair(problems_json: &str) -> PyResult<String> {
    let problems: Vec<Problem> = parse(problems_json)?;
    Ok(turn::repair(&problems))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustDossierStore>()?;
    m.add_function(wrap_pyfunction!(dossier_render, m)?)?;
    m.add_function(wrap_pyfunction!(dossier_parse, m)?)?;
    m.add_function(wrap_pyfunction!(dossier_validate, m)?)?;
    m.add_function(wrap_pyfunction!(dossier_redact, m)?)?;
    m.add_function(wrap_pyfunction!(dossier_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(dossier_step_file, m)?)?;
    m.add_function(wrap_pyfunction!(dossier_prompt, m)?)?;
    m.add_function(wrap_pyfunction!(dossier_check, m)?)?;
    m.add_function(wrap_pyfunction!(dossier_repair, m)?)?;
    Ok(())
}
