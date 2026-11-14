use std::path::PathBuf;

use nuxiva_collaudo_core::{
    Check, CollaudoError, Envelope, Hub, Mode, Query, Redactor, Report, StoreConfig, TokenVault,
    analyze, compare, default_spec, generate, random_key,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_JSON: usize = 4 * 1024 * 1024;

fn fail(error: &CollaudoError) -> PyErr {
    match error {
        CollaudoError::Invalid(_) | CollaudoError::Json(_) => {
            PyValueError::new_err(error.to_string())
        }
        _ => PyRuntimeError::new_err(error.to_string()),
    }
}

fn key_from_hex(value: &str) -> PyResult<[u8; 32]> {
    blake3::Hash::from_hex(value)
        .map(|h| *h.as_bytes())
        .map_err(|_| PyValueError::new_err("collaudo.invalid.key"))
}

fn parse<T: serde::de::DeserializeOwned>(raw: &str) -> PyResult<T> {
    if raw.len() > MAX_JSON {
        return Err(PyValueError::new_err("collaudo.invalid.size"));
    }
    serde_json::from_str(raw).map_err(|_| PyValueError::new_err("collaudo.invalid.json"))
}

fn dump<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|_| PyRuntimeError::new_err("collaudo.serialize"))
}

#[derive(serde::Deserialize, Default)]
#[serde(deny_unknown_fields, default)]
struct QueryArgs {
    since_seq: u64,
    from_ms: Option<u64>,
    to_ms: Option<u64>,
    domain: Option<nuxiva_collaudo_core::Domain>,
    min_level: Option<nuxiva_collaudo_core::Level>,
    corr: Option<String>,
    kind_prefix: Option<String>,
    limit: usize,
}

impl From<QueryArgs> for Query {
    fn from(a: QueryArgs) -> Self {
        Self {
            since_seq: a.since_seq,
            from_ms: a.from_ms,
            to_ms: a.to_ms,
            domain: a.domain,
            min_level: a.min_level,
            corr: a.corr,
            kind_prefix: a.kind_prefix,
            limit: a.limit,
        }
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustCollaudo {
    hub: Hub,
}

#[pymethods]
impl RustCollaudo {
    #[new]
    fn new(
        dir: PathBuf,
        key_hex: &str,
        segment_bytes: u64,
        keep_segments: usize,
    ) -> PyResult<Self> {
        let cfg = StoreConfig {
            dir,
            segment_bytes: segment_bytes.clamp(4096, 256 * 1024 * 1024),
            keep_segments: keep_segments.clamp(1, 512),
            key: key_from_hex(key_hex)?,
        };
        Hub::open(cfg).map(|hub| Self { hub }).map_err(|e| fail(&e))
    }

    fn emit(&self, py: Python<'_>, raw: &str) -> PyResult<Option<u64>> {
        py.detach(|| self.hub.emit_json(raw)).map_err(|e| fail(&e))
    }

    fn query(&self, py: Python<'_>, args: &str) -> PyResult<String> {
        let args: QueryArgs = parse(args)?;
        let events = py
            .detach(|| self.hub.query(&args.into()))
            .map_err(|e| fail(&e))?;
        dump(&events)
    }

    fn set_collaudo(&self, enabled: bool) -> PyResult<()> {
        let mode = if enabled {
            Mode::Collaudo
        } else {
            Mode::Normal
        };
        self.hub.set_mode(mode).map_err(|e| fail(&e))
    }

    fn collaudo(&self) -> PyResult<bool> {
        self.hub
            .mode()
            .map(|m| m == Mode::Collaudo)
            .map_err(|e| fail(&e))
    }

    fn stats(&self) -> PyResult<String> {
        dump(&self.hub.stats().map_err(|e| fail(&e))?)
    }

    fn verify(&self, py: Python<'_>) -> PyResult<String> {
        dump(&py.detach(|| self.hub.verify()).map_err(|e| fail(&e))?)
    }

    fn flush(&self) -> PyResult<()> {
        self.hub.flush().map_err(|e| fail(&e))
    }

    fn anon(&self, scope: &str, value: &str) -> String {
        self.hub.anon(scope, value)
    }

    #[pyo3(signature = (args, spec=None))]
    fn report(&self, py: Python<'_>, args: &str, spec: Option<&str>) -> PyResult<String> {
        let args: QueryArgs = parse(args)?;
        let spec: Vec<Check> = match spec {
            Some(raw) => parse(raw)?,
            None => default_spec(),
        };
        let mut query: Query = args.into();
        query.limit = 5000;
        let events: Vec<Envelope> = py.detach(|| self.hub.query(&query)).map_err(|e| fail(&e))?;
        dump(&analyze(&events, &spec))
    }
}

#[pyfunction]
fn collaudo_default_spec() -> PyResult<String> {
    dump(&default_spec())
}

#[pyfunction]
fn collaudo_compare(before: &str, after: &str) -> PyResult<String> {
    let before: Report = parse(before)?;
    let after: Report = parse(after)?;
    dump(&compare(&before, &after))
}

#[pyfunction]
fn collaudo_scrub_text(value: &str) -> String {
    Redactor::scrub_text(value.get(..value.len().min(4096)).unwrap_or_default())
}

#[pyfunction]
fn collaudo_new_key() -> PyResult<String> {
    random_key()
        .map(|k| blake3::Hash::from_bytes(k).to_hex().to_string())
        .map_err(|e| fail(&e))
}

#[pyfunction]
fn collaudo_token_issue(path: &str) -> PyResult<String> {
    TokenVault::at(std::path::Path::new(path))
        .issue()
        .map_err(|e| fail(&e))
}

#[pyfunction]
fn collaudo_token_verify(path: &str, token: &str) -> bool {
    TokenVault::at(std::path::Path::new(path)).verify(token)
}

#[pyfunction]
fn collaudo_token_revoke(path: &str) -> PyResult<()> {
    TokenVault::at(std::path::Path::new(path))
        .revoke()
        .map_err(|e| fail(&e))
}

#[pyfunction]
fn collaudo_new_secret() -> PyResult<String> {
    generate().map_err(|e| fail(&e))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustCollaudo>()?;
    m.add_function(wrap_pyfunction!(collaudo_default_spec, m)?)?;
    m.add_function(wrap_pyfunction!(collaudo_compare, m)?)?;
    m.add_function(wrap_pyfunction!(collaudo_scrub_text, m)?)?;
    m.add_function(wrap_pyfunction!(collaudo_new_key, m)?)?;
    m.add_function(wrap_pyfunction!(collaudo_new_secret, m)?)?;
    m.add_function(wrap_pyfunction!(collaudo_token_issue, m)?)?;
    m.add_function(wrap_pyfunction!(collaudo_token_verify, m)?)?;
    m.add_function(wrap_pyfunction!(collaudo_token_revoke, m)?)?;
    Ok(())
}
