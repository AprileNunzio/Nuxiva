use std::collections::{BTreeMap, HashMap};
use std::sync::{Arc, Mutex, PoisonError};

use serde_json::Value;
use tokio::sync::Semaphore;
use tokio::task::JoinSet;

use super::context::{
    CODE_BUDGET, CODE_CANCELLED, CODE_GRAPH, CODE_NO_KIND, CODE_OUTPUT, CODE_STALE, CancelToken,
    Meter, StepContext,
};
use super::factory::{Factory, Output, Worker};
use super::supervise::supervise;
use super::throttle::Throttle;
use crate::budget::{FixedBudget, ResourceBudget};
use crate::catalog::Catalog;
use crate::error::{SwarmError, SwarmResult};
use crate::settings::Settings;
use crate::supervisor::{GraphGate, check_budget};
use crate::wire::{
    Ident, Outcome, Phase, Plan, SCHEMA_VERSION, Step, StepEvent, TaskEnvelope, Usage, Validate,
    WorkerError, WorkerErrorKind, WorkerResult,
};

#[derive(Debug, Clone, PartialEq)]
pub struct StepReport {
    pub step: Ident,
    pub outcome: Outcome,
    pub result: Option<WorkerResult>,
    pub error: Option<WorkerError>,
    pub attempts: u32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Report {
    pub steps: Vec<StepReport>,
    pub events: Vec<StepEvent>,
}

impl Report {
    #[must_use]
    pub fn succeeded(&self) -> bool {
        self.steps.iter().all(|s| s.outcome == Outcome::Done)
    }
}

#[derive(Debug)]
pub struct Executor {
    catalog: Arc<Catalog>,
    factory: Arc<Factory>,
    gate: Arc<GraphGate>,
    settings: Settings,
    global: Arc<Throttle>,
    templates: HashMap<Ident, (String, Arc<Semaphore>)>,
}

struct Job {
    task: TaskEnvelope,
    step: Step,
    kind: String,
    inputs: BTreeMap<Ident, Value>,
    cancel: CancelToken,
    now_ms: u64,
}

type Events = Arc<Mutex<Vec<StepEvent>>>;

fn push(events: &Events, task: &Ident, step: &Ident, phase: Phase, at_ms: u64) {
    events
        .lock()
        .unwrap_or_else(PoisonError::into_inner)
        .push(StepEvent {
            schema_version: SCHEMA_VERSION,
            task: task.clone(),
            step: step.clone(),
            phase,
            at_ms,
        });
}

fn failure(step: &Ident, kind: WorkerErrorKind, code: &'static str) -> WorkerError {
    WorkerError::new(kind, Ident::known(code), step.clone())
}

impl Executor {
    #[must_use]
    pub fn new(
        catalog: Arc<Catalog>,
        factory: Arc<Factory>,
        gate: Arc<GraphGate>,
        settings: Settings,
    ) -> Self {
        let budget = Arc::new(FixedBudget(settings.max_workers));
        Self::with_budget(catalog, factory, gate, settings, budget)
    }

    #[must_use]
    pub fn with_budget(
        catalog: Arc<Catalog>,
        factory: Arc<Factory>,
        gate: Arc<GraphGate>,
        settings: Settings,
        budget: Arc<dyn ResourceBudget>,
    ) -> Self {
        let templates = catalog
            .templates()
            .map(|t| {
                let permits = usize::try_from(t.concurrency_max)
                    .unwrap_or(1)
                    .clamp(1, settings.max_workers);
                (
                    t.agent.clone(),
                    (t.kind.clone(), Arc::new(Semaphore::new(permits))),
                )
            })
            .collect();
        let global = Arc::new(Throttle::new(settings.max_workers, budget));
        Self {
            catalog,
            factory,
            gate,
            settings,
            global,
            templates,
        }
    }

    pub async fn run(
        &self,
        task: &TaskEnvelope,
        plan: &Plan,
        now_ms: u64,
        cancel: &CancelToken,
    ) -> SwarmResult<Report> {
        task.validate(&self.settings)?;
        self.catalog.check_plan(plan, &self.settings)?;
        check_budget(plan, task)?;
        let index: HashMap<&str, usize> = plan
            .steps
            .iter()
            .enumerate()
            .map(|(i, s)| (s.id.as_str(), i))
            .collect();
        let count = plan.steps.len();
        let mut indegree = vec![0_usize; count];
        let mut successors: Vec<Vec<usize>> = vec![Vec::new(); count];
        let mut predecessors: Vec<Vec<usize>> = vec![Vec::new(); count];
        for edge in &plan.edges {
            let (Some(&from), Some(&to)) =
                (index.get(edge.from.as_str()), index.get(edge.to.as_str()))
            else {
                return Err(SwarmError::Invalid);
            };
            successors
                .get_mut(from)
                .ok_or(SwarmError::Invalid)?
                .push(to);
            predecessors
                .get_mut(to)
                .ok_or(SwarmError::Invalid)?
                .push(from);
            let slot = indegree.get_mut(to).ok_or(SwarmError::Invalid)?;
            *slot = slot.saturating_add(1);
        }
        let events: Events = Arc::new(Mutex::new(Vec::new()));
        let mut reports: Vec<Option<StepReport>> = vec![None; count];
        let mut outputs: Vec<Option<Value>> = vec![None; count];
        let mut running: JoinSet<(usize, StepReport, Option<Value>)> = JoinSet::new();
        let mut ready: Vec<usize> = (0..count)
            .filter(|i| indegree.get(*i) == Some(&0))
            .collect();
        loop {
            for position in std::mem::take(&mut ready) {
                self.launch(
                    task,
                    plan,
                    position,
                    &predecessors,
                    &outputs,
                    &events,
                    now_ms,
                    cancel,
                    &mut running,
                    &mut reports,
                )?;
            }
            let Some(joined) = running.join_next().await else {
                break;
            };
            let (position, report, output) = joined.map_err(|_| SwarmError::Invalid)?;
            let done = report.outcome == Outcome::Done;
            if let Some(slot) = outputs.get_mut(position) {
                *slot = output;
            }
            if let Some(slot) = reports.get_mut(position) {
                *slot = Some(report);
            }
            if done {
                for &next in successors.get(position).map_or(&[][..], Vec::as_slice) {
                    let Some(left) = indegree.get_mut(next) else {
                        continue;
                    };
                    *left = left.saturating_sub(1);
                    if *left == 0 {
                        ready.push(next);
                    }
                }
            } else {
                Self::skip_descendants(
                    task,
                    plan,
                    position,
                    &successors,
                    &events,
                    now_ms,
                    &mut reports,
                );
            }
        }
        let steps = reports.into_iter().flatten().collect();
        let events = events
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .clone();
        Ok(Report { steps, events })
    }

    fn skip_descendants(
        task: &TaskEnvelope,
        plan: &Plan,
        origin: usize,
        successors: &[Vec<usize>],
        events: &Events,
        now_ms: u64,
        reports: &mut [Option<StepReport>],
    ) {
        let mut stack: Vec<usize> = successors.get(origin).cloned().unwrap_or_default();
        while let Some(position) = stack.pop() {
            let Some(step) = plan.steps.get(position) else {
                continue;
            };
            let Some(slot) = reports.get_mut(position) else {
                continue;
            };
            if slot.is_some() {
                continue;
            }
            *slot = Some(StepReport {
                step: step.id.clone(),
                outcome: Outcome::Cancelled,
                result: None,
                error: None,
                attempts: 0,
            });
            push(events, &task.id, &step.id, Phase::Cancelled, now_ms);
            stack.extend(successors.get(position).cloned().unwrap_or_default());
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn launch(
        &self,
        task: &TaskEnvelope,
        plan: &Plan,
        position: usize,
        predecessors: &[Vec<usize>],
        outputs: &[Option<Value>],
        events: &Events,
        now_ms: u64,
        cancel: &CancelToken,
        running: &mut JoinSet<(usize, StepReport, Option<Value>)>,
        reports: &mut [Option<StepReport>],
    ) -> SwarmResult<()> {
        let step = plan.steps.get(position).ok_or(SwarmError::Invalid)?.clone();
        push(events, &task.id, &step.id, Phase::Queued, now_ms);
        let Some((kind, template_gate)) = self.templates.get(&step.worker_template).cloned() else {
            return Err(SwarmError::UnknownTemplate);
        };
        let inputs: BTreeMap<Ident, Value> = predecessors
            .get(position)
            .map_or(&[][..], Vec::as_slice)
            .iter()
            .filter_map(|p| {
                let id = plan.steps.get(*p)?.id.clone();
                let value = outputs.get(*p)?.clone()?;
                Some((id, value))
            })
            .collect();
        let precheck = self.gate.check(&step, task, now_ms).err().map(|e| {
            let code = if e == SwarmError::GraphStale {
                CODE_STALE
            } else {
                CODE_GRAPH
            };
            failure(&step.id, WorkerErrorKind::GraphNotConsulted, code)
        });
        if let Some(error) = precheck {
            let report = StepReport {
                step: step.id.clone(),
                outcome: Outcome::Failed,
                result: None,
                error: Some(error),
                attempts: 0,
            };
            push(events, &task.id, &step.id, Phase::Failed, now_ms);
            if let Some(slot) = reports.get_mut(position) {
                *slot = Some(report.clone());
            }
            running.spawn(async move { (position, report, None) });
            return Ok(());
        }
        let job = Job {
            task: task.clone(),
            step,
            kind,
            inputs,
            cancel: cancel.clone(),
            now_ms,
        };
        let factory = Arc::clone(&self.factory);
        let global = Arc::clone(&self.global);
        let settings = self.settings.clone();
        let events = Arc::clone(events);
        running.spawn(async move {
            let (report, output) =
                run_job(job, &factory, &global, &template_gate, &settings, &events).await;
            (position, report, output)
        });
        Ok(())
    }
}

struct Finished {
    outcome: Outcome,
    error: Option<WorkerError>,
    attempts: u32,
    result: Option<WorkerResult>,
}

impl Finished {
    fn failed(error: WorkerError, attempts: u32) -> Self {
        let outcome = if error.kind == WorkerErrorKind::Cancelled {
            Outcome::Cancelled
        } else {
            Outcome::Failed
        };
        Self {
            outcome,
            error: Some(error),
            attempts,
            result: None,
        }
    }

    const fn phase(&self) -> Phase {
        match self.outcome {
            Outcome::Done => Phase::Done,
            Outcome::Failed => Phase::Failed,
            Outcome::Cancelled => Phase::Cancelled,
        }
    }
}

async fn run_job(
    job: Job,
    factory: &Factory,
    global: &Throttle,
    template_gate: &Semaphore,
    settings: &Settings,
    events: &Events,
) -> (StepReport, Option<Value>) {
    let id = job.step.id.clone();
    let finished = match (
        factory.get(&job.kind),
        template_gate.acquire().await,
        global.acquire(&job.cancel).await,
    ) {
        (Some(worker), Ok(_template), Some(_global)) => {
            attempts(&job, &worker, settings, events).await
        }
        (None, ..) => Finished::failed(failure(&id, WorkerErrorKind::Unavailable, CODE_NO_KIND), 0),
        (_, _, None) if job.cancel.is_cancelled() => {
            Finished::failed(failure(&id, WorkerErrorKind::Cancelled, CODE_CANCELLED), 0)
        }
        _ => Finished::failed(failure(&id, WorkerErrorKind::Internal, CODE_NO_KIND), 0),
    };
    push(events, &job.task.id, &id, finished.phase(), job.now_ms);
    let output = finished.result.as_ref().map(|r| r.output.clone());
    let report = StepReport {
        step: id,
        outcome: finished.outcome,
        result: finished.result,
        error: finished.error,
        attempts: finished.attempts,
    };
    (report, output)
}

async fn attempts(
    job: &Job,
    worker: &Arc<dyn Worker>,
    settings: &Settings,
    events: &Events,
) -> Finished {
    let id = &job.step.id;
    let mut tried = 0_u32;
    let mut last: Option<WorkerError> = None;
    while tried < settings.step_attempts {
        tried = tried.saturating_add(1);
        if job.cancel.is_cancelled() {
            return Finished::failed(
                failure(id, WorkerErrorKind::Cancelled, CODE_CANCELLED),
                tried,
            );
        }
        push(events, &job.task.id, id, Phase::Started, job.now_ms);
        let meter = Arc::new(Meter::new(job.step.budget));
        let context = StepContext {
            task: job.task.clone(),
            step: job.step.clone(),
            inputs: job.inputs.clone(),
            cancel: job.cancel.clone(),
            meter: Arc::clone(&meter),
            beat: super::context::Beat::new(),
            depth_limit: settings.max_redelegation_depth,
        };
        let outcome = supervise(
            Arc::clone(worker),
            context,
            settings.lease_ms,
            job.step.budget.time_ms,
            job.cancel.clone(),
        )
        .await;
        match finish(outcome, job, meter.usage(), settings) {
            Ok(result) => {
                return Finished {
                    outcome: Outcome::Done,
                    error: None,
                    attempts: tried,
                    result: Some(result),
                };
            }
            Err(error) if error.retryable => last = Some(error),
            Err(error) => return Finished::failed(error, tried),
        }
    }
    match last {
        Some(error) => Finished::failed(error, tried),
        None => Finished::failed(failure(id, WorkerErrorKind::Internal, CODE_NO_KIND), tried),
    }
}

fn finish(
    outcome: Result<Output, WorkerError>,
    job: &Job,
    usage: Usage,
    settings: &Settings,
) -> Result<WorkerResult, WorkerError> {
    let output = outcome?;
    let budget = &job.step.budget;
    if usage.tokens > budget.tokens || usage.tool_calls > budget.tool_calls {
        return Err(failure(
            &job.step.id,
            WorkerErrorKind::BudgetExceeded,
            CODE_BUDGET,
        ));
    }
    let result = WorkerResult {
        schema_version: SCHEMA_VERSION,
        task: job.task.id.clone(),
        step: job.step.id.clone(),
        outcome: Outcome::Done,
        output: output.value,
        evidence: output.evidence,
        usage,
    };
    result
        .validate(settings)
        .map_err(|_| failure(&job.step.id, WorkerErrorKind::Invalid, CODE_OUTPUT))?;
    Ok(result)
}
