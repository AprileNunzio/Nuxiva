use std::sync::RwLock;

use nuxiva_spatial_core::{
    ComponentTracker, Detection, NetlistNet, StabilityGate, validate_netlist,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

fn poisoned() -> PyErr {
    PyRuntimeError::new_err("state is poisoned")
}

fn invalid(error: &serde_json::Error) -> PyErr {
    PyValueError::new_err(error.to_string())
}

fn serialization(error: &serde_json::Error) -> PyErr {
    PyRuntimeError::new_err(error.to_string())
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustWorkbenchTracker {
    gate: RwLock<StabilityGate>,
    tracker: RwLock<ComponentTracker>,
}

#[pymethods]
impl RustWorkbenchTracker {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    fn observe_stability(&self, grid: &[u8]) -> PyResult<&'static str> {
        let mut gate = self.gate.write().map_err(|_| poisoned())?;
        Ok(gate.observe(grid).as_str())
    }

    fn update_tracks_json(&self, detections_json: &str) -> PyResult<String> {
        let detections: Vec<Detection> =
            serde_json::from_str(detections_json).map_err(|e| invalid(&e))?;
        let mut tracker = self.tracker.write().map_err(|_| poisoned())?;
        let tracks = tracker.update(&detections);
        serde_json::to_string(tracks).map_err(|e| serialization(&e))
    }

    fn relabel_track(&self, track_id: u32, label: &str) -> PyResult<bool> {
        let mut tracker = self.tracker.write().map_err(|_| poisoned())?;
        Ok(tracker.relabel(track_id, label))
    }

    fn reset(&self) -> PyResult<()> {
        self.gate.write().map_err(|_| poisoned())?.reset();
        self.tracker.write().map_err(|_| poisoned())?.reset();
        Ok(())
    }
}

#[pyfunction]
pub fn validate_netlist_json(nets_json: &str) -> PyResult<String> {
    let nets: Vec<NetlistNet> = serde_json::from_str(nets_json).map_err(|e| invalid(&e))?;
    serde_json::to_string(&validate_netlist(&nets)).map_err(|e| serialization(&e))
}
