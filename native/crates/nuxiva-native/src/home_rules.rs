use std::collections::{HashMap, HashSet};

use nuxiva_authz_core::{HomeRules, HomeTables, MAX_TARGETS, MAX_TEXT, Risk, Target};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

const MAX_TABLE: usize = 4096;

fn risk(level: u8) -> PyResult<Risk> {
    Risk::from_level(level).ok_or_else(|| PyValueError::new_err("authz.risk.invalid"))
}

fn names(items: Vec<String>) -> PyResult<HashSet<String>> {
    if items.len() > MAX_TABLE || items.iter().any(|s| s.len() > MAX_TEXT) {
        return Err(PyValueError::new_err("authz.home.table_too_large"));
    }
    Ok(items.into_iter().collect())
}

fn targets(raw: &[(String, String)]) -> Vec<Target<'_>> {
    raw.iter()
        .map(|(domain, device_class)| Target {
            domain,
            device_class,
        })
        .collect()
}

fn domains(raw: &[String]) -> Vec<&str> {
    raw.iter().map(String::as_str).collect()
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustHomeRules {
    inner: HomeRules,
}

#[pymethods]
impl RustHomeRules {
    #[new]
    #[allow(clippy::too_many_arguments, clippy::needless_pass_by_value)]
    #[pyo3(signature = (domains, unknown, read_private, sensitive_covers, appliances, climate, gate_open, comfort))]
    fn new(
        domains: HashMap<String, u8>,
        unknown: u8,
        read_private: Vec<String>,
        sensitive_covers: Vec<String>,
        appliances: Vec<String>,
        climate: Vec<String>,
        gate_open: Vec<String>,
        comfort: (f64, f64),
    ) -> PyResult<Self> {
        if domains.len() > MAX_TABLE || domains.keys().any(|k| k.len() > MAX_TEXT) {
            return Err(PyValueError::new_err("authz.home.table_too_large"));
        }
        if !comfort.0.is_finite() || !comfort.1.is_finite() || comfort.0 > comfort.1 {
            return Err(PyValueError::new_err("authz.home.comfort_invalid"));
        }
        let domains = domains
            .into_iter()
            .map(|(k, v)| Ok((k, risk(v)?)))
            .collect::<PyResult<HashMap<_, _>>>()?;
        Ok(Self {
            inner: HomeRules::new(HomeTables {
                domains,
                unknown: risk(unknown)?,
                read_private: names(read_private)?,
                sensitive_covers: names(sensitive_covers)?,
                appliances: names(appliances)?,
                climate: names(climate)?,
                gate_open: names(gate_open)?,
                comfort,
            }),
        })
    }

    #[staticmethod]
    fn max_targets() -> usize {
        MAX_TARGETS
    }

    fn sensitive(&self, domain: &str, service: &str, device_class: &str) -> bool {
        self.inner.sensitive(domain, service, device_class)
    }

    #[allow(clippy::needless_pass_by_value)]
    fn call_risk(&self, declared: &str, service: &str, targets_raw: Vec<(String, String)>) -> u8 {
        self.inner
            .call_risk(declared, service, &targets(&targets_raw)) as u8
    }

    #[allow(clippy::needless_pass_by_value)]
    fn read_risk(&self, entity_domains: Vec<String>) -> u8 {
        self.inner.read_risk(&domains(&entity_domains)) as u8
    }

    #[allow(clippy::needless_pass_by_value)]
    #[pyo3(signature = (declared, service, targets_raw, temperature=None))]
    fn call_capabilities(
        &self,
        declared: &str,
        service: &str,
        targets_raw: Vec<(String, String)>,
        temperature: Option<f64>,
    ) -> Vec<&'static str> {
        self.inner
            .call_capabilities(declared, service, &targets(&targets_raw), temperature)
    }

    #[allow(clippy::needless_pass_by_value)]
    fn read_capability(&self, entity_domains: Vec<String>) -> &'static str {
        self.inner.read_capability(&domains(&entity_domains))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustHomeRules>()
}
