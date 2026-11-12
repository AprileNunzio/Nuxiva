use std::sync::Mutex;

use nuxiva_telemetry_core::{
    MachineClass, MachineInputs, Sampler, core_runtime, detect_class, docker_needed,
    parse_nvidia_smi,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

use crate::errors::poisoned;

const MAX_LIMIT: usize = 256;
const MAX_RAW: usize = 64 * 1024;

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustTelemetry {
    sampler: Mutex<Sampler>,
}

#[pymethods]
impl RustTelemetry {
    #[new]
    fn new() -> Self {
        Self {
            sampler: Mutex::new(Sampler::system()),
        }
    }

    fn sample(&self, py: Python<'_>, now: f64, limit: usize) -> PyResult<String> {
        if !now.is_finite() {
            return Err(PyValueError::new_err("telemetry.time.invalid"));
        }
        let limit = limit.min(MAX_LIMIT);
        let snapshot = py.detach(|| {
            self.sampler
                .lock()
                .map(|mut sampler| sampler.sample(now, limit))
                .ok()
        });
        let snapshot = snapshot.ok_or_else(poisoned)?;
        serde_json::to_string(&snapshot).map_err(|_| PyRuntimeError::new_err("telemetry.serialize"))
    }
}

#[pyfunction]
fn telemetry_parse_nvidia_smi(raw: &str) -> PyResult<Option<String>> {
    if raw.len() > MAX_RAW {
        return Err(PyValueError::new_err("telemetry.input.too_large"));
    }
    parse_nvidia_smi(raw)
        .map(|gpu| serde_json::to_string(&gpu))
        .transpose()
        .map_err(|_| PyRuntimeError::new_err("telemetry.serialize"))
}

#[pyfunction]
fn machine_detect(board: &str, ram_bytes: u64, gpu: bool) -> &'static str {
    detect_class(MachineInputs {
        board,
        ram_bytes,
        gpu,
    })
    .code()
}

#[pyfunction]
fn machine_core_runtime(configured: &str, class: &str) -> PyResult<&'static str> {
    let class =
        MachineClass::parse(class).ok_or_else(|| PyValueError::new_err("machine.class.invalid"))?;
    Ok(core_runtime(configured, class))
}

#[pyfunction]
fn machine_docker_needed(runtime: &str, sandbox: &str) -> bool {
    docker_needed(runtime, sandbox)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustTelemetry>()?;
    m.add_function(wrap_pyfunction!(telemetry_parse_nvidia_smi, m)?)?;
    m.add_function(wrap_pyfunction!(machine_detect, m)?)?;
    m.add_function(wrap_pyfunction!(machine_core_runtime, m)?)?;
    m.add_function(wrap_pyfunction!(machine_docker_needed, m)?)?;
    Ok(())
}
