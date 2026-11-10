use nuxiva_gait_core::{
    evaluate_match, extract_signature, find_best_match, GaitObservation, GaitSignature,
    ReferenceGait,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_INPUT_JSON: usize = 1024 * 1024;

fn bad_arg<E: std::fmt::Display>(e: E) -> PyErr {
    PyValueError::new_err(e.to_string())
}

fn err_rt<E: std::fmt::Display>(e: E) -> PyErr {
    PyRuntimeError::new_err(e.to_string())
}

#[pyclass(module = "nuxiva_native")]
#[derive(Debug, Default)]
pub struct RustGaitCore;

#[pymethods]
#[allow(clippy::unused_self)]
impl RustGaitCore {
    #[new]
    pub fn new() -> Self {
        Self
    }

    pub fn extract(&self, observations_json: &str) -> PyResult<String> {
        if observations_json.len() > MAX_INPUT_JSON {
            return Err(PyValueError::new_err("input json too large"));
        }
        let obs: Vec<GaitObservation> = serde_json::from_str(observations_json).map_err(bad_arg)?;
        let sig = extract_signature(&obs).map_err(bad_arg)?;
        serde_json::to_string(&sig).map_err(err_rt)
    }

    pub fn evaluate(
        &self,
        candidate_json: &str,
        reference_json: &str,
        ref_id: Option<&str>,
        ref_ts_ms: Option<u64>,
    ) -> PyResult<String> {
        if candidate_json.len() > MAX_INPUT_JSON || reference_json.len() > MAX_INPUT_JSON {
            return Err(PyValueError::new_err("input json too large"));
        }
        let cand: GaitSignature = serde_json::from_str(candidate_json).map_err(bad_arg)?;
        let refer: GaitSignature = serde_json::from_str(reference_json).map_err(bad_arg)?;
        let m = evaluate_match(&cand, &refer, ref_id, ref_ts_ms);
        serde_json::to_string(&m).map_err(err_rt)
    }

    pub fn find_best(&self, candidate_json: &str, references_json: &str) -> PyResult<String> {
        if candidate_json.len() > MAX_INPUT_JSON || references_json.len() > MAX_INPUT_JSON {
            return Err(PyValueError::new_err("input json too large"));
        }
        let cand: GaitSignature = serde_json::from_str(candidate_json).map_err(bad_arg)?;
        let refs: Vec<ReferenceGait> = serde_json::from_str(references_json).map_err(bad_arg)?;
        let m = find_best_match(&cand, &refs);
        serde_json::to_string(&m).map_err(err_rt)
    }

    pub fn aggregate(&self, signatures_json: &str) -> PyResult<String> {
        if signatures_json.len() > MAX_INPUT_JSON {
            return Err(PyValueError::new_err("input json too large"));
        }
        let sigs: Vec<GaitSignature> = serde_json::from_str(signatures_json).map_err(bad_arg)?;
        let agg = GaitSignature::aggregate(&sigs).map_err(bad_arg)?;
        serde_json::to_string(&agg).map_err(err_rt)
    }
}
