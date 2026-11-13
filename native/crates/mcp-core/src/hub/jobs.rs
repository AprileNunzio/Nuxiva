use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, PoisonError};
use std::time::{Duration, Instant};

use serde::Serialize;
use tokio::sync::Notify;
use tokio::task::AbortHandle;

use super::{CallOutput, Hub};
use crate::error::{McpError, McpResult};
use crate::payload::{SCHEMA_VERSION, ToolError};
use crate::policy::CallRequest;

enum State {
    Running,
    Done(CallOutput),
    Failed(McpError),
    Cancelled,
}

struct Job {
    agent: String,
    tool: String,
    state: State,
    started: Instant,
    finished: Option<Instant>,
    abort: AbortHandle,
}

#[derive(Debug, Clone, Serialize)]
pub struct JobView {
    pub schema_version: u32,
    pub id: String,
    pub tool: String,
    pub state: &'static str,
    pub elapsed_ms: u64,
    pub output: Option<CallOutput>,
    pub error: Option<ToolError>,
}

#[derive(Debug, Clone)]
pub enum Within {
    Done(Box<CallOutput>),
    Pending(String),
}

pub struct JobTable {
    jobs: Mutex<HashMap<String, Job>>,
    counter: AtomicU64,
    max: usize,
    ttl: Duration,
    finished: Notify,
}

impl std::fmt::Debug for JobTable {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("JobTable").finish_non_exhaustive()
    }
}

fn millis(value: usize) -> Duration {
    Duration::from_millis(u64::try_from(value).unwrap_or(u64::MAX))
}

impl JobTable {
    pub(super) fn new(max: usize, ttl_ms: usize) -> Self {
        Self {
            jobs: Mutex::new(HashMap::new()),
            counter: AtomicU64::new(0),
            max,
            ttl: millis(ttl_ms),
            finished: Notify::new(),
        }
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, HashMap<String, Job>> {
        self.jobs.lock().unwrap_or_else(PoisonError::into_inner)
    }

    fn sweep(&self, jobs: &mut HashMap<String, Job>) {
        let now = Instant::now();
        jobs.retain(|_, job| {
            job.finished
                .is_none_or(|at| now.saturating_duration_since(at) <= self.ttl)
        });
    }

    fn finish(&self, id: &str, outcome: McpResult<CallOutput>) {
        let mut jobs = self.lock();
        if let Some(job) = jobs.get_mut(id) {
            if matches!(job.state, State::Running) {
                job.state = match outcome {
                    Ok(output) => State::Done(output),
                    Err(error) => State::Failed(error),
                };
                job.finished = Some(Instant::now());
            }
        }
        drop(jobs);
        self.finished.notify_waiters();
    }

    fn view(id: &str, job: &Job) -> JobView {
        let elapsed = job
            .finished
            .unwrap_or_else(Instant::now)
            .saturating_duration_since(job.started);
        let (state, output, error) = match &job.state {
            State::Running => ("running", None, None),
            State::Done(out) => ("done", Some(out.clone()), None),
            State::Failed(e) => ("failed", None, Some(ToolError::new(*e, &job.tool))),
            State::Cancelled => ("cancelled", None, None),
        };
        JobView {
            schema_version: SCHEMA_VERSION,
            id: id.to_owned(),
            tool: job.tool.clone(),
            state,
            elapsed_ms: u64::try_from(elapsed.as_millis()).unwrap_or(u64::MAX),
            output,
            error,
        }
    }

    pub fn poll(&self, id: &str, agent: &str) -> McpResult<JobView> {
        let mut jobs = self.lock();
        self.sweep(&mut jobs);
        let job = jobs.get(id).ok_or(McpError::UnknownTool)?;
        if job.agent != agent {
            return Err(McpError::NotPermitted);
        }
        Ok(Self::view(id, job))
    }

    pub fn cancel(&self, id: &str, agent: &str) -> McpResult<()> {
        let mut jobs = self.lock();
        let job = jobs.get_mut(id).ok_or(McpError::UnknownTool)?;
        if job.agent != agent {
            return Err(McpError::NotPermitted);
        }
        if matches!(job.state, State::Running) {
            job.abort.abort();
            job.state = State::Cancelled;
            job.finished = Some(Instant::now());
        }
        drop(jobs);
        self.finished.notify_waiters();
        Ok(())
    }

    #[must_use]
    pub fn running(&self) -> usize {
        self.lock()
            .values()
            .filter(|j| matches!(j.state, State::Running))
            .count()
    }

    fn take_result(&self, id: &str) -> Option<McpResult<CallOutput>> {
        let mut jobs = self.lock();
        let done = jobs
            .get(id)
            .is_some_and(|j| !matches!(j.state, State::Running));
        if !done {
            return None;
        }
        jobs.remove(id).map(|job| match job.state {
            State::Done(out) => Ok(out),
            State::Failed(error) => Err(error),
            _ => Err(McpError::Closed),
        })
    }
}

impl Hub {
    pub fn submit(self: &Arc<Self>, request: CallRequest) -> McpResult<String> {
        let table = &self.jobs;
        let mut jobs = table.lock();
        table.sweep(&mut jobs);
        if jobs
            .values()
            .filter(|j| matches!(j.state, State::Running))
            .count()
            >= table.max
            || jobs.len() >= table.max.saturating_mul(4)
        {
            return Err(McpError::Busy);
        }
        let id = format!(
            "job-{}",
            table
                .counter
                .fetch_add(1, Ordering::Relaxed)
                .saturating_add(1)
        );
        let (agent, tool) = (request.agent.clone(), request.tool.clone());
        let hub = Arc::clone(self);
        let task_id = id.clone();
        let task = tokio::spawn(async move {
            let outcome = hub.call(request).await;
            hub.jobs.finish(&task_id, outcome);
        });
        jobs.insert(
            id.clone(),
            Job {
                agent,
                tool,
                state: State::Running,
                started: Instant::now(),
                finished: None,
                abort: task.abort_handle(),
            },
        );
        Ok(id)
    }

    pub async fn call_within(self: &Arc<Self>, request: CallRequest) -> McpResult<Within> {
        let id = self.submit(request)?;
        let budget = millis(self.settings.foreground_budget_ms);
        let table = &self.jobs;
        let waited = tokio::time::timeout(budget, async {
            loop {
                let notified = table.finished.notified();
                tokio::pin!(notified);
                notified.as_mut().enable();
                if let Some(result) = table.take_result(&id) {
                    return result;
                }
                notified.await;
            }
        })
        .await;
        match waited {
            Ok(result) => result.map(|out| Within::Done(Box::new(out))),
            Err(_) => Ok(Within::Pending(id)),
        }
    }

    pub fn poll(&self, id: &str, agent: &str) -> McpResult<JobView> {
        self.jobs.poll(id, agent)
    }

    pub fn cancel(&self, id: &str, agent: &str) -> McpResult<()> {
        self.jobs.cancel(id, agent)
    }

    #[must_use]
    pub fn running_jobs(&self) -> usize {
        self.jobs.running()
    }
}
