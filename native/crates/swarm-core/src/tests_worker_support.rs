use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use serde_json::{Value, json};
use tokio::time::sleep;

use nuxiva_agent_core::manifest::validate as validate_manifest;

use crate::catalog::Catalog;
use crate::settings::Settings;
use crate::supervisor::GraphGate;
use crate::wire::{
    Constraints, Digest, Edge, Ident, Level, Phase, Plan, SCHEMA_VERSION, Step, StepBudget,
    TaskEnvelope, VerifySpec, WorkerError,
};
use crate::worker::{BoxFuture, Executor, Factory, Output, StepContext, Worker};

pub(crate) fn id(text: &str) -> Ident {
    Ident::new(text).expect("id")
}

pub(crate) type Work =
    dyn Fn(StepContext) -> BoxFuture<'static, Result<Output, WorkerError>> + Send + Sync;

pub(crate) struct Func(Arc<Work>);

impl Worker for Func {
    fn run(&self, context: StepContext) -> BoxFuture<'_, Result<Output, WorkerError>> {
        (self.0)(context)
    }
}

pub(crate) fn worker<F, Fut>(f: F) -> Arc<dyn Worker>
where
    F: Fn(StepContext) -> Fut + Send + Sync + 'static,
    Fut: std::future::Future<Output = Result<Output, WorkerError>> + Send + 'static,
{
    Arc::new(Func(Arc::new(move |c| Box::pin(f(c)))))
}

#[allow(clippy::unnecessary_wraps)]
pub(crate) fn out(value: Value) -> Result<Output, WorkerError> {
    Ok(Output {
        value,
        evidence: Vec::new(),
    })
}

pub(crate) fn echo() -> Arc<dyn Worker> {
    worker(|c| async move {
        c.charge_tokens(10)?;
        c.charge_call()?;
        out(
            json!({"step": c.step.id.as_str(), "inputs": c.inputs.keys().map(Ident::as_str).collect::<Vec<_>>()}),
        )
    })
}

pub(crate) fn manifest(agent: &str, kind: &str, limit: u32, graph: bool) -> String {
    format!(
        r#"{{"id":"{agent}","name":"{agent}","capabilities":["Lavoro"],"worker":{{"kind":"{kind}","concurrency_max":{limit},"needs_graph":{graph}}}}}"#
    )
}

pub(crate) struct Rig {
    pub(crate) executor: Arc<Executor>,
    pub(crate) gate: Arc<GraphGate>,
}

pub(crate) fn rig(settings: &Settings, kinds: &[(&str, u32, bool, Arc<dyn Worker>)]) -> Rig {
    rig_with(settings, kinds, None)
}

pub(crate) fn rig_with(
    settings: &Settings,
    kinds: &[(&str, u32, bool, Arc<dyn Worker>)],
    budget: Option<Arc<dyn crate::ResourceBudget>>,
) -> Rig {
    let mut factory = Factory::new();
    let mut manifests = Vec::new();
    for (kind, limit, graph, w) in kinds {
        factory.register(kind, Arc::clone(w));
        let raw = manifest(&format!("a_{kind}"), kind, *limit, *graph);
        manifests.push(
            validate_manifest(&raw, "x", None)
                .manifest
                .expect("manifest"),
        );
    }
    let catalog = Arc::new(Catalog::build(&manifests, settings).expect("catalog"));
    let gate = Arc::new(GraphGate::new(settings));
    let executor = Arc::new(match budget {
        Some(budget) => Executor::with_budget(
            catalog,
            Arc::new(factory),
            Arc::clone(&gate),
            settings.clone(),
            budget,
        ),
        None => Executor::new(
            catalog,
            Arc::new(factory),
            Arc::clone(&gate),
            settings.clone(),
        ),
    });
    Rig { executor, gate }
}

pub(crate) fn task(graph: Option<Digest>) -> TaskEnvelope {
    TaskEnvelope {
        schema_version: SCHEMA_VERSION,
        id: id("t1"),
        intent: id("lavoro"),
        input: id("in.1"),
        constraints: Constraints {
            risk_max: 2,
            deadline_ms: 600_000,
            tokens_max: 150_000,
            tool_calls_max: 190,
            level: Level::Standard,
        },
        parent: None,
        context_ref: None,
        graph_ref: graph,
        depth: 0,
    }
}

pub(crate) fn step(name: &str, kind: &str, graph: bool) -> Step {
    Step {
        id: id(name),
        worker_template: id(&format!("a_{kind}")),
        intent: id("lavoro"),
        goal_ref: id("in.1"),
        needs_graph: graph,
        budget: StepBudget {
            tokens: 100,
            tool_calls: 5,
            time_ms: 10_000,
        },
        verify: VerifySpec::None,
    }
}

pub(crate) fn plan(steps: Vec<Step>, edges: &[(&str, &str)]) -> Plan {
    Plan {
        schema_version: SCHEMA_VERSION,
        id: id("p-t1"),
        steps,
        edges: edges
            .iter()
            .map(|(a, b)| Edge {
                from: id(a),
                to: id(b),
            })
            .collect(),
    }
}

pub(crate) fn find<'a>(report: &'a crate::Report, name: &str) -> &'a crate::StepReport {
    report
        .steps
        .iter()
        .find(|s| s.step.as_str() == name)
        .expect("step report")
}

pub(crate) fn code(report: &crate::StepReport) -> Option<&str> {
    report.error.as_ref().map(|e| e.code.as_str())
}

pub(crate) fn position(report: &crate::Report, name: &str, phase: Phase) -> usize {
    report
        .events
        .iter()
        .position(|e| e.step.as_str() == name && e.phase == phase)
        .expect("event")
}

pub(crate) fn probe(
    current: &Arc<AtomicUsize>,
    peak: &Arc<AtomicUsize>,
    millis: u64,
) -> Arc<dyn Worker> {
    let (current, peak) = (Arc::clone(current), Arc::clone(peak));
    worker(move |_| {
        let (current, peak) = (Arc::clone(&current), Arc::clone(&peak));
        async move {
            let now = current.fetch_add(1, Ordering::SeqCst) + 1;
            peak.fetch_max(now, Ordering::SeqCst);
            sleep(Duration::from_millis(millis)).await;
            current.fetch_sub(1, Ordering::SeqCst);
            out(json!("ok"))
        }
    })
}

pub(crate) fn resident_kib() -> Option<u64> {
    let raw = std::fs::read_to_string("/proc/self/statm").ok()?;
    raw.split_whitespace()
        .nth(1)?
        .parse::<u64>()
        .ok()
        .map(|pages| pages * 4)
}
