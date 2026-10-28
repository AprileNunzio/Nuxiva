use std::sync::RwLock;

use nuxiva_cortex_core::{
    AbstractionTier, CortexError as CoreError, CorticalCortex, EmbodiedCortex, MotorCommand,
};
use pyo3::prelude::*;

use crate::cortex::CortexError;
use crate::errors::poisoned;

fn failure(error: CoreError) -> PyErr {
    CortexError::new_err(error.code())
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustCorticalCortex {
    inner: RwLock<CorticalCortex>,
}

impl RustCorticalCortex {
    fn read<T>(&self, action: impl FnOnce(&CorticalCortex) -> T) -> PyResult<T> {
        self.inner
            .read()
            .map(|guard| action(&guard))
            .map_err(|_| poisoned())
    }

    fn write<T>(&self, action: impl FnOnce(&mut CorticalCortex) -> T) -> PyResult<T> {
        self.inner
            .write()
            .map(|mut guard| action(&mut guard))
            .map_err(|_| poisoned())
    }
}

#[pymethods]
impl RustCorticalCortex {
    #[new]
    fn new() -> Self {
        Self {
            inner: RwLock::new(CorticalCortex::new()),
        }
    }

    #[staticmethod]
    fn from_snapshot_json(snapshot: &str) -> PyResult<Self> {
        Ok(Self {
            inner: RwLock::new(CorticalCortex::from_snapshot_json(snapshot).map_err(failure)?),
        })
    }

    fn snapshot_json(&self) -> PyResult<String> {
        self.read(CorticalCortex::snapshot_json)?.map_err(failure)
    }

    #[pyo3(signature = (column_id, a, b, c, tier = None))]
    fn solve_quadratic_json(
        &self,
        py: Python<'_>,
        column_id: &str,
        a: f64,
        b: f64,
        c: f64,
        tier: Option<&str>,
    ) -> PyResult<String> {
        let parsed_tier = match tier {
            Some(name) => Some(
                AbstractionTier::from_name(name)
                    .ok_or_else(|| failure(CoreError::InvalidExpression))?,
            ),
            None => None,
        };
        let resolution = py
            .detach(|| {
                self.write(|cortex| cortex.solve_quadratic(column_id, a, b, c, parsed_tier))
            })?
            .map_err(failure)?;
        serde_json::to_string(&resolution).map_err(|_| failure(CoreError::SnapshotInvalid))
    }

    fn consolidate_shortcut_json(
        &self,
        pattern_signature: &str,
        a: f64,
        b: f64,
        c: f64,
    ) -> PyResult<String> {
        let shortcut = self
            .write(|cortex| cortex.consolidate_shortcut(pattern_signature, a, b, c))?
            .map_err(failure)?;
        serde_json::to_string(&shortcut).map_err(|_| failure(CoreError::SnapshotInvalid))
    }
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustEmbodiedCortex {
    inner: RwLock<EmbodiedCortex>,
}

impl RustEmbodiedCortex {
    fn read<T>(&self, action: impl FnOnce(&EmbodiedCortex) -> T) -> PyResult<T> {
        self.inner
            .read()
            .map(|guard| action(&guard))
            .map_err(|_| poisoned())
    }

    fn write<T>(&self, action: impl FnOnce(&mut EmbodiedCortex) -> T) -> PyResult<T> {
        self.inner
            .write()
            .map(|mut guard| action(&mut guard))
            .map_err(|_| poisoned())
    }
}

#[pymethods]
impl RustEmbodiedCortex {
    #[new]
    fn new() -> Self {
        Self {
            inner: RwLock::new(EmbodiedCortex::new()),
        }
    }

    #[staticmethod]
    fn from_snapshot_json(snapshot: &str) -> PyResult<Self> {
        Ok(Self {
            inner: RwLock::new(EmbodiedCortex::from_snapshot_json(snapshot).map_err(failure)?),
        })
    }

    fn snapshot_json(&self) -> PyResult<String> {
        self.read(EmbodiedCortex::snapshot_json)?.map_err(failure)
    }

    #[pyo3(signature = (command_json, measured_angle_override = None))]
    fn step_active_inference_json(
        &self,
        py: Python<'_>,
        command_json: &str,
        measured_angle_override: Option<f64>,
    ) -> PyResult<String> {
        let cmd: MotorCommand = serde_json::from_str(command_json)
            .map_err(|_| failure(CoreError::InvalidExpression))?;
        let step = py
            .detach(|| {
                self.write(|embodied| embodied.step_active_inference(&cmd, measured_angle_override))
            })?
            .map_err(failure)?;
        serde_json::to_string(&step).map_err(|_| failure(CoreError::SnapshotInvalid))
    }
}
