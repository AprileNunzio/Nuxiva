use nuxiva_nvr_core::{ByteRange, parse_range};
use nuxiva_nvr_core::{Catalog, Marker, NvrError, Policy, Segment, Tier, next_marker, plan, spans};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const MAX_JSON: usize = 64 * 1024 * 1024;
const MAX_LIMIT: usize = 20_000;

fn fail(e: &NvrError) -> PyErr {
    PyValueError::new_err(e.code())
}

fn json_err(e: &serde_json::Error) -> PyErr {
    PyValueError::new_err(format!("nvr.json.invalid: {e}"))
}

fn bounded(text: &str) -> PyResult<&str> {
    if text.len() > MAX_JSON {
        return Err(PyValueError::new_err("nvr.json.too_large"));
    }
    Ok(text)
}

fn tier_of(text: &str) -> PyResult<Tier> {
    Tier::parse(text).ok_or_else(|| PyValueError::new_err("nvr.tier.invalid"))
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustNvrCatalog {
    inner: Catalog,
}

#[pymethods]
impl RustNvrCatalog {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    #[staticmethod]
    fn from_json(text: &str) -> PyResult<Self> {
        Ok(Self {
            inner: Catalog::from_json(bounded(text)?).map_err(|e| fail(&e))?,
        })
    }

    fn to_json(&self) -> PyResult<String> {
        self.inner.to_json().map_err(|e| fail(&e))
    }

    fn __len__(&self) -> usize {
        self.inner.len()
    }

    fn insert(&mut self, segment_json: &str) -> PyResult<()> {
        let segment: Segment =
            serde_json::from_str(bounded(segment_json)?).map_err(|e| json_err(&e))?;
        self.inner.insert(segment).map_err(|e| fail(&e))
    }

    fn remove(&mut self, camera: &str, id: &str) -> PyResult<Option<String>> {
        self.inner
            .remove(camera, id)
            .map(|s| serde_json::to_string(&s).map_err(|e| json_err(&e)))
            .transpose()
    }

    fn get(&self, camera: &str, id: &str) -> PyResult<Option<String>> {
        self.inner
            .get(camera, id)
            .map(|s| serde_json::to_string(s).map_err(|e| json_err(&e)))
            .transpose()
    }

    fn set_tier(&mut self, camera: &str, id: &str, tier: &str) -> PyResult<()> {
        self.inner
            .set_tier(camera, id, tier_of(tier)?)
            .map_err(|e| fail(&e))
    }

    fn range(&self, camera: &str, from_ms: u64, to_ms: u64, limit: usize) -> PyResult<String> {
        let rows = self
            .inner
            .range(camera, from_ms, to_ms, limit.min(MAX_LIMIT))
            .map_err(|e| fail(&e))?;
        serde_json::to_string(&rows).map_err(|e| json_err(&e))
    }

    fn seek(&self, camera: &str, at_ms: u64) -> PyResult<Option<String>> {
        self.inner
            .seek(camera, at_ms)
            .map(|s| serde_json::to_string(&s).map_err(|e| json_err(&e)))
            .transpose()
    }

    fn after(&self, camera: &str, id: &str) -> PyResult<Option<String>> {
        self.inner
            .after(camera, id)
            .map(|s| serde_json::to_string(s).map_err(|e| json_err(&e)))
            .transpose()
    }

    fn spans(&self, camera: &str, from_ms: u64, to_ms: u64, tolerance_ms: u64) -> PyResult<String> {
        let rows = self
            .inner
            .range(camera, from_ms, to_ms, MAX_LIMIT)
            .map_err(|e| fail(&e))?;
        serde_json::to_string(&spans(&rows, tolerance_ms)).map_err(|e| json_err(&e))
    }

    fn summary(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner.summary()).map_err(|e| json_err(&e))
    }

    fn total_bytes(&self) -> u64 {
        self.inner.total_bytes()
    }

    fn plan(&self, policy_json: &str, events_json: &str, now_ms: u64) -> PyResult<String> {
        let policy: Policy =
            serde_json::from_str(bounded(policy_json)?).map_err(|e| json_err(&e))?;
        let events: Vec<(String, u64)> =
            serde_json::from_str(bounded(events_json)?).map_err(|e| json_err(&e))?;
        serde_json::to_string(&plan(&self.inner, &policy, &events, now_ms))
            .map_err(|e| json_err(&e))
    }
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
fn nvr_next_marker(
    markers_json: &str,
    at_ms: u64,
    forward: bool,
    kinds: Vec<String>,
) -> PyResult<Option<String>> {
    let markers: Vec<Marker> =
        serde_json::from_str(bounded(markers_json)?).map_err(|e| json_err(&e))?;
    next_marker(&markers, at_ms, forward, &kinds)
        .map(|m| serde_json::to_string(m).map_err(|e| json_err(&e)))
        .transpose()
}

#[pyfunction]
fn nvr_parse_range(header: &str, total: u64) -> (String, u64, u64) {
    match parse_range(header, total) {
        ByteRange::Whole => ("whole".to_owned(), 0, total.saturating_sub(1)),
        ByteRange::Part { start, end } => ("part".to_owned(), start, end),
        ByteRange::Unsatisfiable => ("invalid".to_owned(), 0, 0),
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustNvrCatalog>()?;
    m.add_function(wrap_pyfunction!(nvr_next_marker, m)?)?;
    m.add_function(wrap_pyfunction!(nvr_parse_range, m)?)?;
    Ok(())
}
