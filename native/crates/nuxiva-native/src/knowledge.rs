use std::path::Path;
use std::sync::Arc;

use nuxiva_knowledge_core::{
    KnowledgeSettings, MasterKey, Service, Vault, embed, halve, noisy_or, normalize, system_clock,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::pybacked::PyBackedBytes;

const MAX_PATH: usize = 4096;
const MAX_TEXT: usize = 64 * 1024;

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustKnowledge {
    service: Service,
}

fn invalid(code: &'static str) -> PyErr {
    PyValueError::new_err(code)
}

#[pymethods]
impl RustKnowledge {
    #[new]
    #[pyo3(signature = (key=None, vault_dir=None, settings=None, autosave=true))]
    fn new(
        key: Option<PyBackedBytes>,
        vault_dir: Option<&str>,
        settings: Option<&str>,
        autosave: bool,
    ) -> PyResult<Self> {
        let master = key
            .map(|bytes| {
                let raw: [u8; 32] = (*bytes).try_into().map_err(|_| invalid("knowledge.key"))?;
                Ok::<_, PyErr>(Arc::new(MasterKey::from_key(raw)))
            })
            .transpose()?;
        let parsed = match settings {
            Some(raw) => {
                KnowledgeSettings::from_json(raw).map_err(|error| invalid(error.code()))?
            }
            None => KnowledgeSettings::default(),
        };
        let vault = match (vault_dir, &master) {
            (Some(dir), Some(key)) => {
                if dir.is_empty() || dir.len() > MAX_PATH || dir.contains('\0') {
                    return Err(invalid("knowledge.path"));
                }
                Some(
                    Vault::new(Path::new(dir), Arc::clone(key))
                        .map_err(|error| invalid(error.code()))?,
                )
            }
            (Some(_), None) => return Err(invalid("knowledge.key")),
            (None, _) => None,
        };
        let service = Service::new(parsed, master, vault, system_clock(), autosave)
            .map_err(|error| invalid(error.code()))?;
        Ok(Self { service })
    }

    fn handle(&self, py: Python<'_>, request: &str) -> String {
        py.detach(|| self.service.handle(request))
    }
}

#[pyfunction]
fn knowledge_normalize(text: &str) -> PyResult<String> {
    if text.len() > MAX_TEXT {
        return Err(invalid("knowledge.too_large"));
    }
    Ok(normalize(text))
}

#[pyfunction]
fn knowledge_cosine(a: &str, b: &str) -> PyResult<u32> {
    if a.len() > MAX_TEXT || b.len() > MAX_TEXT {
        return Err(invalid("knowledge.too_large"));
    }
    Ok(embed(a).cosine_permille(&embed(b)))
}

#[pyfunction]
fn knowledge_halve(value: u32, elapsed_ms: u64, half_ms: u64) -> u32 {
    halve(value, elapsed_ms, half_ms)
}

#[pyfunction]
fn knowledge_noisy_or(a: u32, b: u32) -> u32 {
    noisy_or(a, b)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustKnowledge>()?;
    m.add_function(wrap_pyfunction!(knowledge_normalize, m)?)?;
    m.add_function(wrap_pyfunction!(knowledge_cosine, m)?)?;
    m.add_function(wrap_pyfunction!(knowledge_halve, m)?)?;
    m.add_function(wrap_pyfunction!(knowledge_noisy_or, m)?)?;
    Ok(())
}
