use std::collections::{BTreeMap, HashMap};
use std::sync::RwLock;

use nuxiva_authz_core::{MAX_TOOLS, Policy, Risk, RiskTable, Strength};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

const MAX_POLICY: usize = 64 * 1024;

type Export = (
    Vec<(String, &'static str)>,
    Vec<(&'static str, &'static str)>,
);

fn risk(level: u8) -> PyResult<Risk> {
    Risk::from_level(level).ok_or_else(|| PyValueError::new_err("authz.risk.invalid"))
}

fn strength(level: u8) -> PyResult<Strength> {
    Strength::from_level(level).ok_or_else(|| PyValueError::new_err("authz.strength.invalid"))
}

fn lock_error() -> PyErr {
    PyRuntimeError::new_err("authz.state.poisoned")
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustAuthzPolicy {
    inner: RwLock<Policy>,
}

#[pymethods]
impl RustAuthzPolicy {
    #[new]
    #[allow(clippy::needless_pass_by_value)]
    fn new(
        ceiling: HashMap<String, u8>,
        proof: HashMap<u8, u8>,
        subroles: HashMap<String, u8>,
    ) -> PyResult<Self> {
        let ceiling = ceiling
            .into_iter()
            .map(|(k, v)| Ok((k, risk(v)?)))
            .collect::<PyResult<BTreeMap<_, _>>>()?;
        let proof = proof
            .into_iter()
            .map(|(k, v)| Ok((risk(k)?, strength(v)?)))
            .collect::<PyResult<BTreeMap<_, _>>>()?;
        let subroles = subroles
            .into_iter()
            .map(|(k, v)| Ok((k, risk(v)?)))
            .collect::<PyResult<BTreeMap<_, _>>>()?;
        Ok(Self {
            inner: RwLock::new(Policy::new(ceiling, proof, subroles)),
        })
    }

    fn apply(&self, data: &str) -> PyResult<()> {
        if data.len() > MAX_POLICY {
            return Err(PyValueError::new_err("authz.policy.too_large"));
        }
        let parsed: serde_json::Value = serde_json::from_str(data)
            .map_err(|_| PyValueError::new_err("authz.policy.invalid"))?;
        let empty = serde_json::Value::Object(serde_json::Map::new());
        let value = if parsed.is_object() { &parsed } else { &empty };
        self.inner.write().map_err(|_| lock_error())?.apply(value);
        Ok(())
    }

    fn limit(&self, role: &str, subrole: &str, custom: &str) -> PyResult<u8> {
        Ok(self
            .inner
            .read()
            .map_err(|_| lock_error())?
            .limit(role, subrole, custom) as u8)
    }

    fn check(
        &self,
        role: &str,
        subrole: &str,
        custom: &str,
        level: u8,
        wanted: u8,
    ) -> PyResult<(bool, &'static str, u8, u8)> {
        let decision = self.inner.read().map_err(|_| lock_error())?.check(
            role,
            subrole,
            custom,
            strength(level)?,
            risk(wanted)?,
        );
        Ok((
            decision.allowed(),
            decision.verdict.code(),
            decision.risk as u8,
            decision.needed as u8,
        ))
    }

    fn export(&self) -> PyResult<Export> {
        let policy = self.inner.read().map_err(|_| lock_error())?;
        let ceiling = policy
            .ceiling()
            .iter()
            .map(|(k, v)| (k.clone(), v.name()))
            .collect();
        let proof = policy
            .proof()
            .iter()
            .map(|(k, v)| (k.name(), v.name()))
            .collect();
        Ok((ceiling, proof))
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustRiskTable {
    inner: RwLock<RiskTable>,
}

#[pymethods]
impl RustRiskTable {
    #[new]
    #[allow(clippy::needless_pass_by_value)]
    fn new(tools: HashMap<String, u8>) -> PyResult<Self> {
        if tools.len() > MAX_TOOLS {
            return Err(PyValueError::new_err("authz.tools.too_many"));
        }
        let tools = tools
            .into_iter()
            .map(|(k, v)| Ok((k, risk(v)?)))
            .collect::<PyResult<HashMap<_, _>>>()?;
        Ok(Self {
            inner: RwLock::new(RiskTable::new(tools)),
        })
    }

    fn set(&self, name: &str, level: u8) -> PyResult<bool> {
        let level = risk(level)?;
        Ok(self
            .inner
            .write()
            .map_err(|_| lock_error())?
            .set(name, level))
    }

    fn compose(&self, name: &str, steps: Vec<String>) -> PyResult<bool> {
        Ok(self
            .inner
            .write()
            .map_err(|_| lock_error())?
            .compose(name, steps))
    }

    fn forget(&self, name: &str) -> PyResult<()> {
        self.inner.write().map_err(|_| lock_error())?.forget(name);
        Ok(())
    }

    fn of_tool(&self, name: &str) -> PyResult<u8> {
        Ok(self.inner.read().map_err(|_| lock_error())?.of_tool(name) as u8)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustAuthzPolicy>()?;
    m.add_class::<RustRiskTable>()?;
    Ok(())
}
