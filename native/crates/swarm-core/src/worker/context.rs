use std::collections::BTreeMap;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};

use serde_json::Value;
use tokio::sync::watch;
use tokio::time::Instant;

use crate::wire::{Ident, Step, StepBudget, TaskEnvelope, Usage, WorkerError, WorkerErrorKind};

pub const CODE_BUDGET: &str = "swarm.budget.exceeded";
pub const CODE_DEPTH: &str = "swarm.redelegation.depth";
pub const CODE_LEASE: &str = "swarm.lease.expired";
pub const CODE_DEADLINE: &str = "swarm.step.deadline";
pub const CODE_CANCELLED: &str = "swarm.step.cancelled";
pub const CODE_PANIC: &str = "swarm.worker.panic";
pub const CODE_OUTPUT: &str = "swarm.output.invalid";
pub const CODE_NO_KIND: &str = "swarm.worker.no_kind";
pub const CODE_GRAPH: &str = "swarm.graph.not_consulted";
pub const CODE_STALE: &str = "swarm.graph.stale";

#[derive(Debug, Clone)]
pub struct CancelToken {
    sender: Arc<watch::Sender<bool>>,
}

impl Default for CancelToken {
    fn default() -> Self {
        Self::new()
    }
}

impl CancelToken {
    #[must_use]
    pub fn new() -> Self {
        Self {
            sender: Arc::new(watch::channel(false).0),
        }
    }

    pub fn cancel(&self) {
        self.sender.send_replace(true);
    }

    #[must_use]
    pub fn is_cancelled(&self) -> bool {
        *self.sender.borrow()
    }

    #[must_use]
    pub fn subscribe(&self) -> watch::Receiver<bool> {
        self.sender.subscribe()
    }

    pub async fn cancelled(&self) {
        let mut receiver = self.sender.subscribe();
        while !*receiver.borrow_and_update() {
            if receiver.changed().await.is_err() {
                break;
            }
        }
    }
}

#[derive(Debug)]
pub struct Meter {
    budget: StepBudget,
    tokens: AtomicU64,
    calls: AtomicU64,
    started: Instant,
}

impl Meter {
    #[must_use]
    pub fn new(budget: StepBudget) -> Self {
        Self {
            budget,
            tokens: AtomicU64::new(0),
            calls: AtomicU64::new(0),
            started: Instant::now(),
        }
    }

    fn charge(counter: &AtomicU64, amount: u64, limit: u64) -> bool {
        counter
            .try_update(Ordering::AcqRel, Ordering::Acquire, |current| {
                current.checked_add(amount).filter(|next| *next <= limit)
            })
            .is_ok()
    }

    #[must_use]
    pub fn charge_tokens(&self, amount: u64) -> bool {
        Self::charge(&self.tokens, amount, self.budget.tokens)
    }

    #[must_use]
    pub fn charge_call(&self) -> bool {
        Self::charge(&self.calls, 1, self.budget.tool_calls)
    }

    #[must_use]
    pub fn usage(&self) -> Usage {
        Usage {
            tokens: self.tokens.load(Ordering::Acquire),
            tool_calls: self.calls.load(Ordering::Acquire),
            time_ms: u64::try_from(self.started.elapsed().as_millis()).unwrap_or(u64::MAX),
        }
    }
}

#[derive(Debug, Clone)]
pub struct Beat {
    last: Arc<AtomicU64>,
    origin: Instant,
}

impl Default for Beat {
    fn default() -> Self {
        Self::new()
    }
}

impl Beat {
    #[must_use]
    pub fn new() -> Self {
        Self {
            last: Arc::new(AtomicU64::new(0)),
            origin: Instant::now(),
        }
    }

    fn now_ms(&self) -> u64 {
        u64::try_from(self.origin.elapsed().as_millis()).unwrap_or(u64::MAX)
    }

    pub fn pulse(&self) {
        self.last.store(self.now_ms(), Ordering::Release);
    }

    #[must_use]
    pub fn expiry(&self, lease_ms: u64) -> Instant {
        let at = self.last.load(Ordering::Acquire).saturating_add(lease_ms);
        self.origin
            .checked_add(std::time::Duration::from_millis(at))
            .unwrap_or_else(Instant::now)
    }

    #[must_use]
    pub fn idle_ms(&self) -> u64 {
        self.now_ms()
            .saturating_sub(self.last.load(Ordering::Acquire))
    }
}

#[derive(Debug)]
pub struct StepContext {
    pub task: TaskEnvelope,
    pub step: Step,
    pub inputs: BTreeMap<Ident, Value>,
    pub cancel: CancelToken,
    pub(crate) meter: Arc<Meter>,
    pub(crate) beat: Beat,
    pub(crate) depth_limit: usize,
}

impl StepContext {
    #[must_use]
    pub fn error(&self, kind: WorkerErrorKind, code: &'static str) -> WorkerError {
        WorkerError::new(kind, Ident::known(code), self.step.id.clone())
    }

    pub fn charge_tokens(&self, amount: u64) -> Result<(), WorkerError> {
        if self.meter.charge_tokens(amount) {
            Ok(())
        } else {
            Err(self.error(WorkerErrorKind::BudgetExceeded, CODE_BUDGET))
        }
    }

    pub fn charge_call(&self) -> Result<(), WorkerError> {
        if self.meter.charge_call() {
            Ok(())
        } else {
            Err(self.error(WorkerErrorKind::BudgetExceeded, CODE_BUDGET))
        }
    }

    pub fn beat(&self) {
        self.beat.pulse();
    }

    pub fn check_cancel(&self) -> Result<(), WorkerError> {
        if self.cancel.is_cancelled() {
            Err(self.error(WorkerErrorKind::Cancelled, CODE_CANCELLED))
        } else {
            Ok(())
        }
    }

    pub fn child(&self, intent: Ident, input: Ident) -> Result<TaskEnvelope, WorkerError> {
        let depth = self.task.depth.saturating_add(1);
        if usize::from(depth) > self.depth_limit {
            return Err(self.error(WorkerErrorKind::Denied, CODE_DEPTH));
        }
        let mut child = self.task.clone();
        child.parent = Some(self.task.id.clone());
        child.intent = intent;
        child.input = input;
        child.depth = depth;
        Ok(child)
    }
}
