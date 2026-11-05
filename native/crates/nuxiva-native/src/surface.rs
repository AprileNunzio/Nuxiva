use crate::errors::poisoned;
use nuxiva_surface_core::layout::Screen;
use nuxiva_surface_core::{Layout, MoveGuard, MoveOrigin, RoomAudience};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde::Serialize;
use std::collections::BTreeMap;
use std::sync::Mutex;

const MAX_INPUT: usize = 256 * 1024;

#[derive(Serialize)]
struct Placement<'a> {
    room: Option<&'a str>,
    left: Option<u8>,
    right: Option<u8>,
    up: Option<u8>,
    down: Option<u8>,
}

fn bad<E: std::fmt::Display>(e: E) -> PyErr {
    PyValueError::new_err(e.to_string())
}

fn sized(raw: &str) -> PyResult<&str> {
    if raw.len() > MAX_INPUT {
        Err(PyValueError::new_err("surface input too large"))
    } else {
        Ok(raw)
    }
}

#[pyfunction]
pub fn surface_layout(screens_json: &str) -> PyResult<String> {
    let screens: Vec<Screen> = serde_json::from_str(sized(screens_json)?).map_err(bad)?;
    let layout = Layout::new(screens);
    let map: BTreeMap<String, Placement<'_>> = layout
        .numbers()
        .into_iter()
        .map(|n| {
            let around = layout.neighbors(n);
            (
                n.to_string(),
                Placement {
                    room: layout.room_of(n),
                    left: around.left,
                    right: around.right,
                    up: around.up,
                    down: around.down,
                },
            )
        })
        .collect();
    serde_json::to_string(&map).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
#[pyo3(signature = (audience_json, room = None))]
pub fn surface_audience(audience_json: &str, room: Option<&str>) -> PyResult<String> {
    let audience: RoomAudience = serde_json::from_str(sized(audience_json)?).map_err(bad)?;
    serde_json::to_string(&audience.for_room(room))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug)]
pub struct RustMoveGuard {
    inner: Mutex<MoveGuard>,
}

#[pymethods]
impl RustMoveGuard {
    #[new]
    #[pyo3(signature = (hold_ms = nuxiva_surface_core::moves::HOLD_MS))]
    fn new(hold_ms: u64) -> Self {
        Self {
            inner: Mutex::new(MoveGuard::new(hold_ms)),
        }
    }

    #[allow(clippy::needless_pass_by_value)]
    fn decide(
        &self,
        key: &str,
        wanted: u8,
        origin: &str,
        now_ms: u64,
        alive: Vec<u8>,
    ) -> PyResult<u8> {
        if key.is_empty() || key.len() > 256 {
            return Err(PyValueError::new_err("invalid widget key"));
        }
        let origin = match origin {
            "user" => MoveOrigin::User,
            "planner" => MoveOrigin::Planner,
            _ => return Err(PyValueError::new_err("invalid move origin")),
        };
        let mut guard = self.inner.lock().map_err(|_| poisoned())?;
        Ok(guard.decide(key, wanted, origin, now_ms, &alive))
    }

    #[allow(clippy::needless_pass_by_value)]
    fn forget(&self, alive_keys: Vec<String>) -> PyResult<()> {
        self.inner
            .lock()
            .map_err(|_| poisoned())?
            .forget(&alive_keys);
        Ok(())
    }
}
