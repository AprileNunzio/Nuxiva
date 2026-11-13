use std::sync::RwLock;

use nuxiva_defense_core::{GeoTable, assess_json, geo::MAX_ROWS};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_GEO_BYTES: u64 = 256 * 1024 * 1024;
const MAX_BATCH: usize = 4096;

#[pyfunction]
pub fn defense_assess(py: Python<'_>, raw: &str) -> PyResult<String> {
    let owned = raw.to_owned();
    py.detach(move || assess_json(&owned))
        .map_err(|e| PyValueError::new_err(e.code()))
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustGeo {
    table: RwLock<GeoTable>,
}

fn read(path: &str) -> Result<String, &'static str> {
    let meta = std::fs::metadata(path).map_err(|_| "geo.missing")?;
    if !meta.is_file() || meta.len() > MAX_GEO_BYTES {
        return Err("geo.too_large");
    }
    std::fs::read_to_string(path).map_err(|_| "geo.unreadable")
}

#[pymethods]
impl RustGeo {
    #[new]
    fn new() -> Self {
        Self {
            table: RwLock::new(GeoTable::default()),
        }
    }

    fn load(&self, py: Python<'_>, path: &str) -> PyResult<usize> {
        let owned = path.to_owned();
        let table = py
            .detach(move || {
                read(&owned).and_then(|text| {
                    GeoTable::parse(&text).map_err(nuxiva_defense_core::GeoError::code)
                })
            })
            .map_err(PyValueError::new_err)?;
        let size = table.len();
        *self
            .table
            .write()
            .map_err(|_| PyRuntimeError::new_err("geo.poisoned"))? = table;
        Ok(size)
    }

    fn parse(&self, text: &str) -> PyResult<usize> {
        if text.lines().count() > MAX_ROWS {
            return Err(PyValueError::new_err("geo.too_large"));
        }
        let table = GeoTable::parse(text).map_err(|e| PyValueError::new_err(e.code()))?;
        let size = table.len();
        *self
            .table
            .write()
            .map_err(|_| PyRuntimeError::new_err("geo.poisoned"))? = table;
        Ok(size)
    }

    fn lookup(&self, address: &str) -> PyResult<Option<String>> {
        Ok(self
            .table
            .read()
            .map_err(|_| PyRuntimeError::new_err("geo.poisoned"))?
            .lookup(address))
    }

    fn lookup_many(&self, addresses: Vec<String>) -> PyResult<Vec<Option<String>>> {
        if addresses.len() > MAX_BATCH {
            return Err(PyValueError::new_err("geo.batch"));
        }
        let table = self
            .table
            .read()
            .map_err(|_| PyRuntimeError::new_err("geo.poisoned"))?;
        Ok(addresses.into_iter().map(|a| table.lookup(&a)).collect())
    }

    fn size(&self) -> PyResult<usize> {
        Ok(self
            .table
            .read()
            .map_err(|_| PyRuntimeError::new_err("geo.poisoned"))?
            .len())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(defense_assess, m)?)?;
    m.add_class::<RustGeo>()?;
    Ok(())
}
