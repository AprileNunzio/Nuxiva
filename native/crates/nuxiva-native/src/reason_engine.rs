use std::collections::BTreeMap;
use std::path::Path;
use std::sync::{Mutex, MutexGuard};

use capability_registry::Role;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use reason_engine::{
    Checked, Config, Engine, Ledger, Mode, Prepared, Sample, SealedJournal, Switch, Verdict,
};
use reason_exec::{ApprovalGate, Call, Executor, Failure, Invoker, Never, Report, Status};
use serde_json::{Value, json};

const JOURNAL_LIMIT: usize = 4_096;
const MAX_INPUT_BYTES: usize = 64 * 1024;

fn invalid(error: impl std::fmt::Display) -> PyErr {
    PyValueError::new_err(error.to_string())
}

fn bounded(text: &str) -> PyResult<&str> {
    if text.len() > MAX_INPUT_BYTES {
        return Err(PyValueError::new_err("reason.input.too_large"));
    }
    Ok(text)
}

fn role(text: &str) -> PyResult<Role> {
    serde_json::from_value(Value::String(text.to_owned()))
        .map_err(|_| PyValueError::new_err("reason.role.unknown"))
}

fn checked_json(checked: &Checked) -> Value {
    json!({
        "plan": checked.plan,
        "hash": checked.hash,
        "cached": checked.cached,
        "executable": checked.executable(),
        "levels": checked.validated.levels,
        "missing": checked.validated.missing,
        "approvals": checked.validated.approvals,
        "capabilities": checked.plan.steps.iter().filter_map(|s| s.capability.clone()).collect::<Vec<_>>(),
    })
}

fn status_key(status: &Status) -> &'static str {
    match status {
        Status::Done(_) => "done",
        Status::Replayed(_) => "replayed",
        Status::Failed => "failed",
        Status::Denied => "denied",
        Status::Indeterminate => "indeterminate",
        Status::Missing => "missing",
        Status::Skipped => "skipped",
        Status::Cancelled => "cancelled",
    }
}

fn report_json(report: &Report) -> Value {
    let steps: Vec<Value> = report
        .steps
        .iter()
        .map(|s| {
            json!({
                "step": s.step,
                "status": status_key(&s.status),
                "output": s.status.output(),
                "attempts": s.attempts,
            })
        })
        .collect();
    json!({ "complete": report.complete(), "needs_human": report.needs_human(), "steps": steps })
}

struct DenyAll;

impl ApprovalGate for DenyAll {
    fn approve(&mut self, _: &str, _: &str, _: &BTreeMap<String, String>) -> bool {
        false
    }
}

struct PyInvoker {
    callable: Py<PyAny>,
    error: Option<PyErr>,
}

fn failure(text: &str) -> Failure {
    match text {
        "retryable" => Failure::Retryable,
        "not_started" => Failure::NotStarted,
        _ => Failure::Permanent,
    }
}

impl Invoker for PyInvoker {
    fn invoke(&mut self, call: &Call<'_>) -> Result<String, Failure> {
        let args = serde_json::to_string(call.args).map_err(|_| Failure::NotStarted)?;
        Python::attach(|py| {
            let raw: String = match self
                .callable
                .call1(py, (call.capability, call.key, args))
                .and_then(|out| out.extract(py))
            {
                Ok(raw) => raw,
                Err(error) => {
                    self.error.get_or_insert(error);
                    return Err(Failure::Permanent);
                }
            };
            let parsed: Value = serde_json::from_str(&raw).map_err(|_| Failure::Permanent)?;
            if parsed.get("ok").and_then(Value::as_bool) == Some(true) {
                return Ok(parsed
                    .get("output")
                    .and_then(Value::as_str)
                    .unwrap_or_default()
                    .to_owned());
            }
            Err(failure(
                parsed
                    .get("failure")
                    .and_then(Value::as_str)
                    .unwrap_or_default(),
            ))
        })
    }
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustReasonEngine {
    inner: Mutex<Engine>,
}

impl RustReasonEngine {
    fn engine(&self) -> PyResult<MutexGuard<'_, Engine>> {
        self.inner
            .lock()
            .map_err(|_| PyRuntimeError::new_err("reason.engine.poisoned"))
    }
}

#[pymethods]
impl RustReasonEngine {
    #[new]
    #[pyo3(signature = (config_json=None))]
    fn new(config_json: Option<&str>) -> PyResult<Self> {
        let config = match config_json {
            Some(raw) => Config::parse(raw).map_err(invalid)?,
            None => Config::default(),
        };
        Ok(Self {
            inner: Mutex::new(Engine::new(config)),
        })
    }

    fn configure(&self, config_json: &str) -> PyResult<()> {
        let config = Config::parse(config_json).map_err(invalid)?;
        self.engine()?.configure(config).map_err(invalid)
    }

    fn config(&self) -> PyResult<String> {
        Ok(json!(self.engine()?.config()).to_string())
    }

    fn load_registry(&self, document: &str) -> PyResult<usize> {
        self.engine()?
            .load_registry(document.as_bytes())
            .map_err(invalid)
    }

    fn generation(&self) -> PyResult<u64> {
        Ok(self.engine()?.registry().generation())
    }

    #[staticmethod]
    #[pyo3(signature = (user, external=None))]
    fn understand_request(user: &str, external: Option<&str>) -> PyResult<String> {
        let request = Engine::understand_request(user, external).map_err(invalid)?;
        Ok(json!({ "system": request.system, "user": request.user, "external": request.external, "schema": request.schema }).to_string())
    }

    #[staticmethod]
    fn goal(raw_goal: &str, user: &str) -> PyResult<String> {
        let goal = Engine::goal(bounded(raw_goal)?, user).map_err(invalid)?;
        Ok(json!(goal).to_string())
    }

    fn prepare(
        &self,
        raw_goal: &str,
        user: &str,
        role_name: &str,
        now_ms: u64,
    ) -> PyResult<String> {
        let goal = Engine::goal(bounded(raw_goal)?, user).map_err(invalid)?;
        let role = role(role_name)?;
        Ok(match self.engine()?.prepare(&goal, user, role, now_ms) {
            Prepared::Cached(checked) => {
                json!({ "kind": "cached", "checked": checked_json(&checked) })
            }
            Prepared::Ask(request) => json!({ "kind": "ask", "request": request }),
        }
        .to_string())
    }

    #[allow(clippy::too_many_arguments)]
    fn accept(
        &self,
        raw_goal: &str,
        user: &str,
        role_name: &str,
        raw_plan: &str,
        listed_json: &str,
        attempt: u8,
        now_ms: u64,
    ) -> PyResult<String> {
        let goal = Engine::goal(bounded(raw_goal)?, user).map_err(invalid)?;
        let role = role(role_name)?;
        let listed: Vec<String> = serde_json::from_str(bounded(listed_json)?).map_err(invalid)?;
        let mut engine = self.engine()?;
        Ok(
            match engine.accept(&goal, user, role, bounded(raw_plan)?, &listed, attempt) {
                Verdict::Accepted(checked) => {
                    engine.remember(&goal, &checked, now_ms);
                    json!({ "kind": "accepted", "checked": checked_json(&checked) })
                }
                Verdict::Retry { code, request } => {
                    json!({ "kind": "retry", "code": code, "request": request })
                }
                Verdict::Rejected(code) => json!({ "kind": "rejected", "code": code }),
            }
            .to_string(),
        )
    }

    #[staticmethod]
    fn compare(plan_json: &str, legacy_json: &str) -> PyResult<String> {
        let plan = reason_plan::parse(bounded(plan_json)?).map_err(invalid)?;
        let legacy: Vec<String> = serde_json::from_str(bounded(legacy_json)?).map_err(invalid)?;
        let refs: Vec<&str> = legacy.iter().map(String::as_str).collect();
        let agreement = Engine::compare(&plan, &refs);
        Ok(json!({ "shared": agreement.shared, "only_new": agreement.only_new, "only_old": agreement.only_old, "matches": agreement.matches() }).to_string())
    }

    fn record(&self, sample_json: &str, now_ms: u64) -> PyResult<()> {
        let sample: Sample = serde_json::from_str(bounded(sample_json)?).map_err(invalid)?;
        self.engine()?.record(&sample, now_ms);
        Ok(())
    }

    fn status(&self, now_ms: u64) -> PyResult<String> {
        let engine = self.engine()?;
        let (size, hits, misses) = engine.cache_stats();
        Ok(json!({
            "gate": engine.status(now_ms),
            "switch": engine.mode(),
            "capabilities": engine.registry().len(),
            "generation": engine.registry().generation(),
            "cache": { "size": size, "hits": hits, "misses": misses },
        })
        .to_string())
    }

    fn set_mode(&self, mode: &str, force: bool, now_ms: u64) -> PyResult<String> {
        let target = Mode::parse(mode).map_err(invalid)?;
        let mut engine = self.engine()?;
        engine.set_mode(target, force, now_ms).map_err(invalid)?;
        Ok(json!(engine.mode()).to_string())
    }

    fn restore(&self, switch_json: &str) -> PyResult<()> {
        let switch: Switch = serde_json::from_str(bounded(switch_json)?).map_err(invalid)?;
        self.engine()?.restore(switch);
        Ok(())
    }

    fn kill(&self) -> PyResult<()> {
        self.engine()?.kill();
        Ok(())
    }

    fn ledger(&self) -> PyResult<String> {
        self.engine()?.ledger().to_json().map_err(invalid)
    }

    fn load_ledger(&self, raw: &str) -> PyResult<()> {
        let ledger = Ledger::parse(raw).map_err(invalid)?;
        self.engine()?.load_ledger(ledger);
        Ok(())
    }

    fn reset_ledger(&self) -> PyResult<()> {
        self.engine()?.reset_ledger();
        Ok(())
    }

    #[allow(clippy::too_many_arguments)]
    fn execute(
        &self,
        py: Python<'_>,
        raw_goal: &str,
        user: &str,
        role_name: &str,
        plan_json: &str,
        journal_dir: &str,
        key: &[u8],
        invoker: Py<PyAny>,
    ) -> PyResult<String> {
        let key: [u8; 32] = key
            .try_into()
            .map_err(|_| PyValueError::new_err("reason.journal.key"))?;
        let goal = Engine::goal(bounded(raw_goal)?, user).map_err(invalid)?;
        let role = role(role_name)?;
        let (registry, checked) = {
            let engine = self.engine()?;
            let checked = engine
                .check(&goal, role, bounded(plan_json)?, None)
                .map_err(PyValueError::new_err)?;
            (engine.registry().clone(), checked)
        };
        if !checked.executable() {
            return Err(PyValueError::new_err("reason.plan.not_executable"));
        }
        let path = Path::new(journal_dir).join(format!("{}.journal", checked.hash));
        let mut caller = PyInvoker {
            callable: invoker,
            error: None,
        };
        let outcome = py.detach(|| {
            let journal = SealedJournal::open(&path, key, JOURNAL_LIMIT)?;
            let mut executor = Executor::new(&registry, &mut caller, DenyAll, journal, Never);
            executor.run(&checked.plan, &checked.validated, &goal, &checked.hash)
        });
        if let Some(error) = caller.error.take() {
            return Err(error);
        }
        let report = outcome.map_err(invalid)?;
        Ok(report_json(&report).to_string())
    }
}

impl Invoker for &mut PyInvoker {
    fn invoke(&mut self, call: &Call<'_>) -> Result<String, Failure> {
        (**self).invoke(call)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustReasonEngine>()?;
    Ok(())
}
