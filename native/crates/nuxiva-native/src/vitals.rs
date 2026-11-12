use pyo3::prelude::*;

#[pyfunction]
pub fn vitals_parse_ble_heart_rate(frame: &[u8]) -> (Option<f64>, Option<f64>) {
    let sample = nuxiva_vitals_core::parse_heart_rate_measurement(frame);
    (sample.heart_rate_bpm, sample.hrv_rmssd_ms)
}
