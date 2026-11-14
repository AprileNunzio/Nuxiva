use nuxiva_chat_core::IntentTable;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustIntents {
    table: IntentTable,
}

#[pymethods]
impl RustIntents {
    #[new]
    fn new() -> PyResult<Self> {
        IntentTable::new()
            .map(|table| Self { table })
            .map_err(|error| PyValueError::new_err(error.to_string()))
    }

    fn detect(&self, py: Python<'_>, text: &str) -> &'static str {
        py.detach(|| self.table.detect(text).name)
    }

    fn names(&self) -> Vec<&'static str> {
        self.table.names().collect()
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustIntents>()
}
