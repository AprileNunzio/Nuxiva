use nuxiva_access_core::origin::{is_host_origin, normalized_locals};
use nuxiva_access_core::{Capability, Matrix, Request, Role, Strength, Verdict, decide};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_CAPABILITIES: usize = 64;

fn strength(raw: &str) -> Strength {
    match raw {
        "strong" => Strength::Strong,
        "single" => Strength::Single,
        "weak" => Strength::Weak,
        _ => Strength::None,
    }
}

const fn name(level: Strength) -> &'static str {
    match level {
        Strength::None => "none",
        Strength::Weak => "weak",
        Strength::Single => "single",
        Strength::Strong => "strong",
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustAccessMatrix {
    matrix: Matrix,
}

#[pymethods]
impl RustAccessMatrix {
    #[new]
    #[pyo3(signature = (raw = None))]
    fn new(raw: Option<&str>) -> PyResult<Self> {
        let matrix = match raw {
            Some(text) => Matrix::parse(text),
            None => Matrix::builtin(),
        }
        .map_err(|e| PyValueError::new_err(e.code()))?;
        Ok(Self { matrix })
    }

    #[pyo3(signature = (capabilities, role, level, local = None, own = false))]
    fn decide(
        &self,
        capabilities: Vec<String>,
        role: &str,
        level: &str,
        local: Option<bool>,
        own: bool,
    ) -> PyResult<(String, String)> {
        if capabilities.len() > MAX_CAPABILITIES {
            return Err(PyValueError::new_err("access.error.too_many"));
        }
        let parsed: Vec<Capability> = capabilities
            .into_iter()
            .map(|c| Capability::parse(&c).map_err(|e| PyValueError::new_err(e.code())))
            .collect::<PyResult<_>>()?;
        let req = Request {
            capabilities: &parsed,
            role: Role::parse(role),
            strength: strength(level),
            local,
            own,
        };
        Ok(match decide(&req, &self.matrix) {
            Verdict::Allow => ("allow".into(), String::new()),
            Verdict::Confirm => ("confirm".into(), String::new()),
            Verdict::NeedProof(level) => ("proof".into(), name(level).into()),
            Verdict::Deny(code) => ("deny".into(), code.into()),
        })
    }

    fn export(&self) -> PyResult<String> {
        serde_json::to_string(&self.matrix.export())
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

#[pyfunction]
#[allow(clippy::needless_pass_by_value)]
pub fn access_is_host_origin(peer: &str, host: &str, locals: Vec<String>) -> bool {
    is_host_origin(peer, host, &normalized_locals(&locals))
}
