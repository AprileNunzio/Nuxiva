use std::path::Path;

use nuxiva_graph_core::GraphSettings;
use nuxiva_mcp_core::ToolServer;
use nuxiva_mcp_servers::{DirSource, GraphServer};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde_json::{Map, Value};

const MAX_ARGS: usize = 64 * 1024;
const MAX_ROOT: usize = 4096;

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustGraph {
    server: GraphServer,
}

#[pymethods]
impl RustGraph {
    #[new]
    fn new(root: &str) -> PyResult<Self> {
        if root.is_empty() || root.len() > MAX_ROOT || root.contains('\0') {
            return Err(PyValueError::new_err("graph.root"));
        }
        let source =
            DirSource::new(Path::new(root)).map_err(|error| PyValueError::new_err(error.code()))?;
        let server = GraphServer::new(
            "graph",
            &GraphSettings::default(),
            std::sync::Arc::new(source),
        )
        .map_err(|_| PyRuntimeError::new_err("graph.settings.invalid"))?;
        Ok(Self { server })
    }

    fn tools(&self) -> PyResult<String> {
        serde_json::to_string(&self.server.tools())
            .map_err(|_| PyRuntimeError::new_err("graph.serialize"))
    }

    fn call(&self, py: Python<'_>, name: &str, arguments: &str) -> PyResult<(bool, String)> {
        if arguments.len() > MAX_ARGS {
            return Err(PyValueError::new_err("graph.arguments"));
        }
        let parsed: Value = serde_json::from_str(arguments)
            .map_err(|_| PyValueError::new_err("graph.arguments"))?;
        let args: Map<String, Value> = match parsed {
            Value::Object(map) => map,
            _ => return Err(PyValueError::new_err("graph.arguments")),
        };
        let output = py.detach(|| self.server.call(name, &args));
        Ok((output.is_error, output.text))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustGraph>()
}
