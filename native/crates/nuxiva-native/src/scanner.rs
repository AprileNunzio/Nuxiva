use pyo3::prelude::*;

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct FastScanner {
    inner: nuxiva_bus_core::FastScannerRegistry,
}

#[pymethods]
impl FastScanner {
    #[new]
    fn new() -> Self {
        Self {
            inner: nuxiva_bus_core::FastScannerRegistry::new(),
        }
    }

    fn scan(&self, py: Python<'_>, root_dir: &str, target_file: &str) -> PyResult<Py<PyAny>> {
        let report = self.inner.scan_directory(root_dir, target_file);
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("total", report.total)?;
        dict.set_item("added", report.added)?;
        dict.set_item("modified", report.modified)?;
        dict.set_item("removed", report.removed)?;
        let entries = pyo3::types::PyList::empty(py);
        for e in report.entries {
            let entry_dict = pyo3::types::PyDict::new(py);
            entry_dict.set_item("id", e.id)?;
            entry_dict.set_item("path", e.path)?;
            entry_dict.set_item("fingerprint", e.fingerprint)?;
            entry_dict.set_item("is_dir", e.is_dir)?;
            entries.append(entry_dict)?;
        }
        dict.set_item("entries", entries)?;
        Ok(dict.into())
    }

    fn invalidate(&self, id: &str) -> bool {
        self.inner.invalidate(id)
    }

    fn clear(&self) {
        self.inner.clear();
    }
}
