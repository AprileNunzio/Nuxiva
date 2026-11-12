use crate::errors::poisoned;
use nuxiva_creations_core::{Archive, ArchiveError, NewEntry, shard, tokens};
use pyo3::exceptions::{PyOSError, PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::path::Path;
use std::sync::Mutex;

const MAX_JSON: usize = 64 * 1024;

fn json<T: serde::Serialize>(value: &T) -> PyResult<String> {
    serde_json::to_string(value).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

fn failure(e: ArchiveError) -> PyErr {
    if e.0.starts_with("invalid") {
        PyValueError::new_err(e.0)
    } else {
        PyOSError::new_err(e.0)
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustCreationArchive {
    inner: Mutex<Archive>,
}

#[pymethods]
impl RustCreationArchive {
    #[new]
    fn new(path: &str) -> PyResult<Self> {
        let archive = Archive::open(Path::new(path)).map_err(failure)?;
        Ok(Self {
            inner: Mutex::new(archive),
        })
    }

    fn put(&self, py: Python<'_>, entry_json: &str, now: i64) -> PyResult<String> {
        if entry_json.len() > MAX_JSON {
            return Err(PyValueError::new_err("invalid entry: too large"));
        }
        let entry: NewEntry = serde_json::from_str(entry_json)
            .map_err(|e| PyValueError::new_err(format!("invalid entry: {e}")))?;
        let saved = py.detach(|| {
            self.inner
                .lock()
                .map_err(|_| poisoned())
                .map(|mut a| a.put(&entry, now))
        })?;
        json(&saved.map_err(failure)?)
    }

    fn lookup(&self, py: Python<'_>, key: &str, now: i64) -> PyResult<Option<String>> {
        let found = py.detach(|| {
            self.inner
                .lock()
                .map_err(|_| poisoned())
                .map(|mut a| a.lookup(key, now))
        })?;
        found.map_err(failure)?.map(|e| json(&e)).transpose()
    }

    fn search(&self, py: Python<'_>, query: &str, limit: usize) -> PyResult<String> {
        let hits = py.detach(|| {
            self.inner
                .lock()
                .map_err(|_| poisoned())
                .map(|a| a.search(query, limit))
        })?;
        json(&hits.map_err(failure)?)
    }

    fn recent(&self, py: Python<'_>, limit: usize) -> PyResult<String> {
        let rows = py.detach(|| {
            self.inner
                .lock()
                .map_err(|_| poisoned())
                .map(|a| a.recent(limit))
        })?;
        json(&rows.map_err(failure)?)
    }

    fn count(&self) -> PyResult<u64> {
        let archive = self.inner.lock().map_err(|_| poisoned())?;
        archive.count().map_err(failure)
    }

    fn evict(&self, py: Python<'_>, keep: usize) -> PyResult<Vec<String>> {
        let orphans = py.detach(|| {
            self.inner
                .lock()
                .map_err(|_| poisoned())
                .map(|mut a| a.evict(keep))
        })?;
        orphans.map_err(failure)
    }
}

#[pyfunction]
pub fn creations_shard(digest: &str) -> Option<String> {
    shard(digest)
}

#[pyfunction]
pub fn creations_tokens(text: &str, limit: usize) -> Vec<String> {
    tokens(text, limit.min(64))
}
