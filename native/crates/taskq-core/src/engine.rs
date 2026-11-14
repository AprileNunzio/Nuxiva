use std::collections::{HashMap, VecDeque};
use std::future::Future;
use std::pin::Pin;
use std::sync::{Arc, Condvar, Mutex, MutexGuard, PoisonError};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use tokio::runtime::{Builder, Handle, Runtime};

use crate::cancel::{CancelToken, Progress};
use crate::error::{TaskqError, TaskqResult};
use crate::journal::Journal;
use crate::queue::{Change, ClassCounts, Queue, Submitted};
use crate::settings::Settings;
use crate::spec::{Class, ErrorPayload, TaskEvent, TaskSpec};

pub type BoxFuture<T> = Pin<Box<dyn Future<Output = T> + Send>>;

pub trait Executor: Send + Sync + 'static {
    fn run(
        &self,
        spec: TaskSpec,
        cancel: CancelToken,
        progress: Progress,
    ) -> BoxFuture<Result<Vec<String>, ErrorPayload>>;
}

pub trait Clock: Send + Sync + 'static {
    fn now_ms(&self) -> u64;
}

#[derive(Debug)]
pub struct SystemClock {
    origin: Instant,
}

impl SystemClock {
    #[must_use]
    pub fn new() -> Self {
        Self {
            origin: Instant::now(),
        }
    }
}

impl Default for SystemClock {
    fn default() -> Self {
        Self::new()
    }
}

impl Clock for SystemClock {
    fn now_ms(&self) -> u64 {
        u64::try_from(self.origin.elapsed().as_millis()).unwrap_or(u64::MAX)
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Stats {
    pub voice: ClassCounts,
    pub interactive: ClassCounts,
    pub background: ClassCounts,
    pub maintenance: ClassCounts,
    pub journal_errors: u64,
    pub dropped_events: u64,
}

struct Running {
    cancel: CancelToken,
    progress: Progress,
}

struct State {
    queue: Queue,
    journal: Box<dyn Journal>,
    running: HashMap<String, Running>,
    events: VecDeque<TaskEvent>,
    event_cap: usize,
    dropped: u64,
    journal_errors: u64,
    compacted_at: u64,
    shutdown: bool,
}

struct Inner {
    state: Mutex<State>,
    wake: Condvar,
    clock: Arc<dyn Clock>,
    executor: Arc<dyn Executor>,
    handles: [Handle; 4],
}

pub struct Engine {
    inner: Arc<Inner>,
    runtimes: Vec<Runtime>,
    ticker: Option<JoinHandle<()>>,
}

impl std::fmt::Debug for Engine {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Engine").finish_non_exhaustive()
    }
}

fn lock(state: &Mutex<State>) -> MutexGuard<'_, State> {
    state.lock().unwrap_or_else(PoisonError::into_inner)
}

impl Inner {
    fn flush(&self, st: &mut State) {
        let changes = st.queue.drain();
        if changes.is_empty() {
            return;
        }
        let now = self.clock.now_ms();
        if st.journal.append(now, &changes).is_err() {
            st.journal_errors = st.journal_errors.saturating_add(1);
        }
        for change in changes {
            if let Change::State { event } = change {
                if st.events.len() >= st.event_cap {
                    st.events.pop_front();
                    st.dropped = st.dropped.saturating_add(1);
                }
                st.events.push_back(event);
            }
        }
        let size = st.journal.size();
        if size > st.journal.soft_limit() && size > st.compacted_at.saturating_mul(2) {
            let live = st.queue.compact_changes();
            if st.journal.compact(now, &live).is_err() {
                st.journal_errors = st.journal_errors.saturating_add(1);
            }
            st.compacted_at = st.journal.size();
        }
    }

    fn signal(st: &State, ids: &[String]) {
        for id in ids {
            if let Some(run) = st.running.get(id) {
                run.cancel.cancel();
            }
        }
    }

    fn pump(self: &Arc<Self>, st: &mut State) {
        if st.shutdown {
            return;
        }
        let now = self.clock.now_ms();
        st.queue.tick(now);
        for class in Class::ALL {
            while let Some(dispatch) = st.queue.pop(class, now) {
                let cancel = CancelToken::new();
                let progress = Progress::default();
                st.running.insert(
                    dispatch.spec.id.clone(),
                    Running {
                        cancel: cancel.clone(),
                        progress: progress.clone(),
                    },
                );
                let Some(handle) = self.handles.get(class.index()) else {
                    continue;
                };
                let inner = Arc::clone(self);
                let id = dispatch.spec.id.clone();
                let wall = Duration::from_millis(dispatch.spec.budget.wall_ms);
                let fut = self.executor.run(dispatch.spec, cancel.clone(), progress);
                handle.spawn(async move {
                    let join = tokio::spawn(fut);
                    let abort = join.abort_handle();
                    let outcome = tokio::select! {
                        r = join => r.unwrap_or_else(|_| Err(ErrorPayload::new("taskq.panic", false))),
                        () = cancel.cancelled() => {
                            abort.abort();
                            Err(ErrorPayload::new("taskq.cancelled", false))
                        }
                        () = tokio::time::sleep(wall) => {
                            abort.abort();
                            Err(ErrorPayload::new("taskq.deadline", false))
                        }
                    };
                    inner.finish(&id, outcome);
                });
            }
        }
        self.flush(st);
    }

    fn finish(self: &Arc<Self>, id: &str, outcome: Result<Vec<String>, ErrorPayload>) {
        let mut st = lock(&self.state);
        st.running.remove(id);
        if st.shutdown {
            return;
        }
        let now = self.clock.now_ms();
        let result = match outcome {
            Ok(evidence) => st.queue.complete(id, evidence, now),
            Err(error) => st.queue.fail(id, error, now),
        };
        if let Ok(signals) = result {
            Self::signal(&st, &signals);
        }
        self.pump(&mut st);
        self.wake.notify_all();
    }
}

fn runtime(class: Class, threads: usize) -> TaskqResult<Runtime> {
    Builder::new_multi_thread()
        .worker_threads(threads)
        .thread_name(format!("nuxiva-taskq-{}", class.name()))
        .enable_time()
        .build()
        .map_err(|_| TaskqError::Settings)
}

impl Engine {
    pub fn start(
        settings: Settings,
        executor: Arc<dyn Executor>,
        mut journal: Box<dyn Journal>,
        clock: Arc<dyn Clock>,
    ) -> TaskqResult<Self> {
        settings.validate()?;
        let mut runtimes = Vec::with_capacity(4);
        for class in Class::ALL {
            runtimes.push(runtime(class, settings.limits(class).threads)?);
        }
        let handles = [
            runtimes
                .first()
                .ok_or(TaskqError::Settings)?
                .handle()
                .clone(),
            runtimes
                .get(1)
                .ok_or(TaskqError::Settings)?
                .handle()
                .clone(),
            runtimes
                .get(2)
                .ok_or(TaskqError::Settings)?
                .handle()
                .clone(),
            runtimes
                .get(3)
                .ok_or(TaskqError::Settings)?
                .handle()
                .clone(),
        ];
        let now = clock.now_ms();
        let loaded = journal.load()?;
        let event_cap = settings.event_log;
        let mut queue = Queue::restore(settings, loaded, now)?;
        let recovery = queue.drain();
        if !recovery.is_empty() {
            journal.append(now, &recovery)?;
        }
        let state = State {
            queue,
            journal,
            running: HashMap::new(),
            events: VecDeque::new(),
            event_cap,
            dropped: 0,
            journal_errors: 0,
            compacted_at: 0,
            shutdown: false,
        };
        let inner = Arc::new(Inner {
            state: Mutex::new(state),
            wake: Condvar::new(),
            clock,
            executor,
            handles,
        });
        {
            let mut st = lock(&inner.state);
            inner.pump(&mut st);
        }
        let ticker_inner = Arc::clone(&inner);
        let ticker = std::thread::Builder::new()
            .name("nuxiva-taskq-ticker".into())
            .spawn(move || Self::tick_loop(&ticker_inner))
            .map_err(|_| TaskqError::Settings)?;
        Ok(Self {
            inner,
            runtimes,
            ticker: Some(ticker),
        })
    }

    fn tick_loop(inner: &Arc<Inner>) {
        let mut st = lock(&inner.state);
        while !st.shutdown {
            inner.pump(&mut st);
            let now = inner.clock.now_ms();
            let wait = st
                .queue
                .next_wake()
                .map_or(60_000, |at| at.saturating_sub(now).clamp(1, 60_000));
            st = inner
                .wake
                .wait_timeout(st, Duration::from_millis(wait))
                .unwrap_or_else(PoisonError::into_inner)
                .0;
        }
    }

    pub fn submit(&self, spec: TaskSpec) -> TaskqResult<Submitted> {
        let mut st = lock(&self.inner.state);
        if st.shutdown {
            return Err(TaskqError::Shutdown);
        }
        let id = spec.id.clone();
        let now = self.inner.clock.now_ms();
        let outcome = st.queue.submit(spec, now)?;
        if outcome == Submitted::Accepted {
            let changes = st.queue.drain();
            if st.journal.append(now, &changes).is_err() {
                st.journal_errors = st.journal_errors.saturating_add(1);
                let _ = st.queue.cancel(&id);
                st.queue.drain();
                return Err(TaskqError::Journal);
            }
            for change in changes {
                if let Change::State { event } = change {
                    if st.events.len() >= st.event_cap {
                        st.events.pop_front();
                        st.dropped = st.dropped.saturating_add(1);
                    }
                    st.events.push_back(event);
                }
            }
        }
        self.inner.pump(&mut st);
        Ok(outcome)
    }

    pub fn submit_json(&self, text: &str) -> TaskqResult<Submitted> {
        self.submit(TaskSpec::from_json(text)?)
    }

    pub fn cancel(&self, id: &str) -> TaskqResult<()> {
        let mut st = lock(&self.inner.state);
        let signals = st.queue.cancel(id)?;
        Inner::signal(&st, &signals);
        self.inner.pump(&mut st);
        Ok(())
    }

    #[must_use]
    pub fn status(&self, id: &str) -> Option<TaskEvent> {
        let st = lock(&self.inner.state);
        let mut event = st.queue.state(id)?;
        if let Some(run) = st.running.get(id) {
            event.progress = run.progress.get();
        }
        Some(event)
    }

    #[must_use]
    pub fn drain_events(&self, max: usize) -> Vec<TaskEvent> {
        let mut st = lock(&self.inner.state);
        let take = max.min(st.events.len());
        st.events.drain(..take).collect()
    }

    #[must_use]
    pub fn stats(&self) -> Stats {
        let st = lock(&self.inner.state);
        Stats {
            voice: st.queue.counts(Class::Voice),
            interactive: st.queue.counts(Class::Interactive),
            background: st.queue.counts(Class::Background),
            maintenance: st.queue.counts(Class::Maintenance),
            journal_errors: st.journal_errors,
            dropped_events: st.dropped,
        }
    }

    pub fn shutdown(&mut self) {
        self.stop(None);
    }

    pub fn shutdown_wait(&mut self, wait: Duration) {
        self.stop(Some(wait));
    }

    fn stop(&mut self, wait: Option<Duration>) {
        {
            let mut st = lock(&self.inner.state);
            st.shutdown = true;
            for run in st.running.values() {
                run.cancel.cancel();
            }
        }
        self.inner.wake.notify_all();
        if let Some(ticker) = self.ticker.take() {
            let _ = ticker.join();
        }
        for runtime in self.runtimes.drain(..) {
            match wait {
                Some(limit) => runtime.shutdown_timeout(limit),
                None => runtime.shutdown_background(),
            }
        }
    }
}

impl Drop for Engine {
    fn drop(&mut self) {
        self.shutdown();
    }
}
