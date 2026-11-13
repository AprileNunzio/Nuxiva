use nuxiva_weather_core::{Forecast, MAX_ITEMS, Observation, Situation, insights, verify};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde::Deserialize;

const MAX_INPUT: usize = 4 * 1024 * 1024;

#[derive(Deserialize)]
struct VerifyInput {
    forecasts: Vec<Forecast>,
    observed: Vec<Observation>,
    #[serde(default)]
    lead: Option<u32>,
    #[serde(default)]
    min_pairs: u32,
}

fn guard(raw: &str) -> PyResult<()> {
    if raw.len() > MAX_INPUT {
        return Err(PyValueError::new_err("weather input too large"));
    }
    Ok(())
}

#[pyfunction]
pub fn weather_verify(input_json: &str) -> PyResult<String> {
    guard(input_json)?;
    let input: VerifyInput =
        serde_json::from_str(input_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    if input.forecasts.len() > MAX_ITEMS.saturating_mul(4) || input.observed.len() > MAX_ITEMS {
        return Err(PyValueError::new_err("too many weather items"));
    }
    let verdict = verify(
        &input.forecasts,
        &input.observed,
        input.lead,
        input.min_pairs,
    );
    serde_json::to_string(&verdict).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
pub fn weather_insights(situation_json: &str) -> PyResult<String> {
    guard(situation_json)?;
    let situation: Situation =
        serde_json::from_str(situation_json).map_err(|e| PyValueError::new_err(e.to_string()))?;
    if situation.hourly.len() > MAX_ITEMS
        || situation.nowcast.len() > MAX_ITEMS
        || situation.days.len() > MAX_ITEMS
    {
        return Err(PyValueError::new_err("too many weather items"));
    }
    serde_json::to_string(&insights(&situation)).map_err(|e| PyRuntimeError::new_err(e.to_string()))
}
