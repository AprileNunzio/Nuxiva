use std::collections::BTreeSet;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, PoisonError, RwLock};

use nuxiva_agent_core::ceo::{self, Index, Learned};
use nuxiva_mcp_core::Hub;
use nuxiva_swarm_core::{
    Admission, CancelToken, Catalog, Executor, Factory, GraphGate, Ident, Plan, Report, Request,
    Settings, Supervisor, TaskEnvelope, Worker,
};

use crate::error::{BrainError, BrainResult};
use crate::worker::{McpWorker, Pending, Utterance};

const MAX_TEXT_BYTES: usize = 8 * 1024;
const RISK_CEILING: u8 = 2;

#[derive(Debug, Clone, PartialEq)]
pub enum Dispatched {
    Conversation,
    Executed {
        task: String,
        succeeded: bool,
        steps: usize,
    },
}

pub struct Dispatcher {
    supervisor: Supervisor,
    executor: Arc<Executor>,
    index: Index,
    learned: RwLock<Learned>,
    pending: Pending,
    cancel: RwLock<CancelToken>,
    counter: AtomicU64,
}

impl std::fmt::Debug for Dispatcher {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("Dispatcher(..)")
    }
}

fn swarm<E: std::fmt::Display>(error: E) -> BrainError {
    BrainError::Dispatch(error.to_string())
}

impl Dispatcher {
    pub fn new(
        catalog: Catalog,
        settings: Settings,
        index: Index,
        hub: Arc<Hub>,
    ) -> BrainResult<Self> {
        let pending = Pending::default();
        let worker: Arc<dyn Worker> = Arc::new(McpWorker::new(hub, pending.clone()));
        let kinds: BTreeSet<String> = catalog.templates().map(|t| t.kind.clone()).collect();
        let mut factory = Factory::new();
        for kind in &kinds {
            factory.register(kind, Arc::clone(&worker));
        }
        let supervisor = Supervisor::new(catalog.clone(), settings.clone()).map_err(swarm)?;
        let gate = Arc::new(GraphGate::new(&settings));
        let executor = Arc::new(Executor::new(
            Arc::new(catalog),
            Arc::new(factory),
            gate,
            settings,
        ));
        Ok(Self {
            supervisor,
            executor,
            index,
            learned: RwLock::new(Learned::new()),
            pending,
            cancel: RwLock::new(CancelToken::new()),
            counter: AtomicU64::new(0),
        })
    }

    pub fn cancel_all(&self) {
        let mut guard = self.cancel.write().unwrap_or_else(PoisonError::into_inner);
        guard.cancel();
        *guard = CancelToken::new();
    }

    fn next_id(&self, prefix: &str) -> BrainResult<Ident> {
        let n = self.counter.fetch_add(1, Ordering::Relaxed);
        Ident::new(&format!("{prefix}-{n}")).map_err(swarm)
    }

    pub async fn dispatch(
        &self,
        text: &str,
        principal: &str,
        now_ms: u64,
    ) -> BrainResult<Dispatched> {
        if text.is_empty() || text.len() > MAX_TEXT_BYTES || text.chars().any(char::is_control) {
            return Err(BrainError::Input("text"));
        }
        let decision = {
            let learned = self.learned.read().unwrap_or_else(PoisonError::into_inner);
            ceo::decide(&self.index, text, &learned)
        };
        let id = self.next_id("task")?;
        let request = Request {
            id: id.clone(),
            input: self.next_id("input")?,
            text,
            context_ref: None,
            graph_ref: None,
            risk_max: RISK_CEILING,
        };
        let admission = self.supervisor.admit(&decision, &request).map_err(swarm)?;
        let task = match admission {
            Admission::Direct => return Ok(Dispatched::Conversation),
            Admission::Task(task) => *task,
        };
        let plan = self
            .supervisor
            .plan(&task, &decision, text, None, now_ms)
            .map_err(swarm)?;
        self.run(task, plan, text, principal, now_ms).await
    }

    async fn run(
        &self,
        task: TaskEnvelope,
        plan: Plan,
        text: &str,
        principal: &str,
        now_ms: u64,
    ) -> BrainResult<Dispatched> {
        let key = task.id.as_str().to_owned();
        let stored = self.pending.insert(
            &key,
            Utterance {
                text: text.to_owned(),
                principal: principal.to_owned(),
            },
        );
        if !stored {
            return Err(BrainError::QueueFull);
        }
        let token = self
            .cancel
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .clone();
        let outcome = self.executor.run(&task, &plan, now_ms, &token).await;
        self.pending.remove(&key);
        let report: Report = outcome.map_err(swarm)?;
        Ok(Dispatched::Executed {
            task: key,
            succeeded: report.succeeded(),
            steps: report.steps.len(),
        })
    }
}
