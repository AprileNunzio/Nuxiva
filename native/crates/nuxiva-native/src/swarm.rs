use std::collections::BTreeSet;
use std::sync::{Arc, Mutex, PoisonError, RwLock};
use std::time::Duration;

use nuxiva_agent_core::ceo::{self, Card, Decision, Index, Learned};
use nuxiva_agent_core::manifest::validate as validate_manifest;
use nuxiva_swarm_core::{
    Admission, BoxFuture, CancelToken, Catalog, Digest, Executor, Factory, GraphGate, Ident,
    Output, Plan, PressureBudget, Request, ResourceBudget, Settings, StepContext, Supervisor,
    SwarmError, TaskEnvelope, Worker, WorkerError, WorkerErrorKind,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde_json::{Value, json};
use tokio::runtime::{Builder, Runtime};

const MAX_JSON: usize = 16 * 1024 * 1024;
const BEAT: Duration = Duration::from_secs(1);
const CODE_BRIDGE: &str = "swarm.bridge.failed";
const CODE_REPLY: &str = "swarm.bridge.reply";

fn fail(error: SwarmError) -> PyErr {
    PyValueError::new_err(error.code())
}

fn bad(message: &str) -> PyErr {
    PyValueError::new_err(message.to_owned())
}

fn parse<T: serde::de::DeserializeOwned>(raw: &str) -> PyResult<T> {
    if raw.len() > MAX_JSON {
        return Err(bad("payload too large"));
    }
    serde_json::from_str(raw).map_err(|_| bad("payload invalid"))
}

fn dump(value: &Value) -> PyResult<String> {
    serde_json::to_string(value).map_err(|_| bad("serialize"))
}

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct Meta {
    id: String,
    input: String,
    risk_max: u8,
    #[serde(default)]
    graph_ref: Option<String>,
}

struct BridgeWorker {
    callback: Py<PyAny>,
}

impl BridgeWorker {
    fn failure(context: &StepContext, kind: WorkerErrorKind, code: &str) -> WorkerError {
        let code = Ident::new(code).unwrap_or_else(|_| context.step.id.clone());
        WorkerError::new(kind, code, context.step.id.clone())
    }

    fn interpret(context: &StepContext, reply: &str) -> Result<Output, WorkerError> {
        let Ok(Value::Object(mut object)) = serde_json::from_str::<Value>(reply) else {
            return Err(Self::failure(
                context,
                WorkerErrorKind::Internal,
                CODE_REPLY,
            ));
        };
        if let Some(error) = object.get("error").and_then(Value::as_object) {
            let kind = error
                .get("kind")
                .cloned()
                .and_then(|v| serde_json::from_value::<WorkerErrorKind>(v).ok())
                .unwrap_or(WorkerErrorKind::Internal);
            let code = error
                .get("code")
                .and_then(Value::as_str)
                .unwrap_or(CODE_BRIDGE);
            return Err(Self::failure(context, kind, code));
        }
        let evidence = object
            .get("evidence")
            .and_then(Value::as_array)
            .map(|list| {
                list.iter()
                    .filter_map(Value::as_str)
                    .filter_map(|s| Ident::new(s).ok())
                    .collect()
            })
            .unwrap_or_default();
        let value = object.remove("output").unwrap_or(Value::Null);
        Ok(Output { value, evidence })
    }
}

impl Worker for BridgeWorker {
    fn run(&self, context: StepContext) -> BoxFuture<'_, Result<Output, WorkerError>> {
        let callback = Python::attach(|py| self.callback.clone_ref(py));
        Box::pin(async move {
            context.charge_call()?;
            context.check_cancel()?;
            let payload = json!({
                "task": context.task.id,
                "step": context.step.id,
                "agent": context.step.worker_template,
                "intent": context.step.intent,
                "goal": context.step.goal_ref,
                "inputs": context.inputs,
            })
            .to_string();
            let mut call = tokio::task::spawn_blocking(move || {
                Python::attach(|py| callback.call1(py, (payload,))?.extract::<String>(py))
            });
            let reply = loop {
                tokio::select! {
                    joined = &mut call => break joined,
                    () = tokio::time::sleep(BEAT) => context.beat(),
                }
            };
            match reply {
                Ok(Ok(text)) => Self::interpret(&context, &text),
                _ => Err(Self::failure(
                    &context,
                    WorkerErrorKind::Unavailable,
                    CODE_BRIDGE,
                )),
            }
        })
    }
}

fn decision_json(decision: &Decision) -> Value {
    json!({
        "conversational": decision.conversational,
        "primary": decision.primary,
        "secondaries": decision.secondaries,
        "confidence": decision.confidence,
        "level": decision.level,
        "needs_reasoning": decision.needs_reasoning,
    })
}

#[pyclass(module = "nuxiva_native", frozen)]
#[derive(Debug)]
pub struct RustSwarm {
    runtime: Runtime,
    supervisor: Supervisor,
    executor: Arc<Executor>,
    gate: Arc<GraphGate>,
    index: Index,
    learned: RwLock<Learned>,
    cancel: Mutex<CancelToken>,
    budget: Arc<PressureBudget>,
}

#[pymethods]
#[allow(clippy::needless_pass_by_value)]
impl RustSwarm {
    #[new]
    #[pyo3(signature = (manifests_json, cards_json, callback, settings_json = ""))]
    fn new(
        manifests_json: &str,
        cards_json: &str,
        callback: Py<PyAny>,
        settings_json: &str,
    ) -> PyResult<Self> {
        let settings = if settings_json.is_empty() {
            Settings::default()
        } else {
            Settings::from_json(settings_json).map_err(fail)?
        };
        let raws: Vec<Value> = parse(manifests_json)?;
        let manifests: Vec<_> = raws
            .iter()
            .filter_map(|raw| {
                let text = serde_json::to_string(raw).ok()?;
                let folder = raw.get("id").and_then(Value::as_str).unwrap_or("x");
                validate_manifest(&text, folder, None).manifest
            })
            .collect();
        let catalog = Catalog::build(&manifests, &settings).map_err(fail)?;
        let cards: Vec<Card> = parse(cards_json)?;
        let kinds: BTreeSet<String> = catalog.templates().map(|t| t.kind.clone()).collect();
        let mut factory = Factory::new();
        let worker: Arc<dyn Worker> = Arc::new(BridgeWorker { callback });
        for kind in &kinds {
            factory.register(kind, Arc::clone(&worker));
        }
        let supervisor = Supervisor::new(catalog.clone(), settings.clone()).map_err(fail)?;
        let gate = Arc::new(GraphGate::new(&settings));
        let budget = Arc::new(PressureBudget::new(settings.max_workers));
        let executor = Arc::new(Executor::with_budget(
            Arc::new(catalog),
            Arc::new(factory),
            Arc::clone(&gate),
            settings,
            Arc::clone(&budget) as Arc<dyn ResourceBudget>,
        ));
        let runtime = Builder::new_multi_thread()
            .worker_threads(2)
            .enable_time()
            .build()
            .map_err(|_| bad("runtime"))?;
        Ok(Self {
            runtime,
            supervisor,
            executor,
            gate,
            index: Index::new(cards),
            learned: RwLock::new(Learned::new()),
            cancel: Mutex::new(CancelToken::new()),
            budget,
        })
    }

    fn set_learned(&self, learned_json: &str) -> PyResult<()> {
        let table: Learned = parse(learned_json)?;
        *self.learned.write().map_err(|_| bad("poisoned"))? = table;
        Ok(())
    }

    fn issue_graph_ref(&self, digest: &str, now_ms: u64) -> PyResult<()> {
        let digest = Digest::try_from(digest.to_owned()).map_err(fail)?;
        self.gate.issue(digest, now_ms);
        Ok(())
    }

    fn admit(&self, py: Python<'_>, text: &str, meta_json: &str, now_ms: u64) -> PyResult<String> {
        let meta: Meta = parse(meta_json)?;
        let decision = {
            let learned = self.learned.read().map_err(|_| bad("poisoned"))?;
            py.detach(|| ceo::decide(&self.index, text, &learned))
        };
        let graph = match meta.graph_ref.as_deref().filter(|g| !g.is_empty()) {
            Some(raw) => Some(Digest::try_from(raw.to_owned()).map_err(fail)?),
            None => None,
        };
        let request = Request {
            id: Ident::new(&meta.id).map_err(fail)?,
            input: Ident::new(&meta.input).map_err(fail)?,
            text,
            context_ref: None,
            graph_ref: graph,
            risk_max: meta.risk_max,
        };
        let admission = self.supervisor.admit(&decision, &request).map_err(fail)?;
        let reply = match admission {
            Admission::Direct => json!({"kind": "direct", "decision": decision_json(&decision)}),
            Admission::Task(task) => {
                let planned = self.supervisor.plan(&task, &decision, text, None, now_ms);
                let (plan, plan_error) = match planned {
                    Ok(plan) => (serde_json::to_value(plan).ok(), None),
                    Err(error) => (None, Some(error.code())),
                };
                json!({
                    "kind": "task",
                    "decision": decision_json(&decision),
                    "task": serde_json::to_value(&*task).map_err(|_| bad("serialize"))?,
                    "plan": plan,
                    "plan_error": plan_error,
                })
            }
        };
        dump(&reply)
    }

    fn execute(
        &self,
        py: Python<'_>,
        task_json: &str,
        plan_json: &str,
        now_ms: u64,
    ) -> PyResult<String> {
        let task: TaskEnvelope = parse(task_json)?;
        let plan: Plan = parse(plan_json)?;
        let token = CancelToken::new();
        *self.cancel.lock().unwrap_or_else(PoisonError::into_inner) = token.clone();
        let executor = Arc::clone(&self.executor);
        let report = py
            .detach(|| {
                self.runtime
                    .block_on(async move { executor.run(&task, &plan, now_ms, &token).await })
            })
            .map_err(fail)?;
        let steps: Vec<Value> = report
            .steps
            .iter()
            .map(|s| {
                json!({
                    "step": s.step,
                    "outcome": s.outcome,
                    "attempts": s.attempts,
                    "result": s.result,
                    "error": s.error,
                })
            })
            .collect();
        dump(&json!({"succeeded": report.succeeded(), "steps": steps, "events": report.events}))
    }

    fn set_pressure(&self, rank: u8) {
        self.budget.set_rank(rank);
    }

    fn pressure(&self) -> u8 {
        self.budget.rank()
    }

    fn cancel(&self) {
        self.cancel
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .cancel();
    }

    fn __len__(&self) -> usize {
        self.index.len()
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RustSwarm>()
}
