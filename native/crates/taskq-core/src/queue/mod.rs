mod finish;
mod restore;

use std::cmp::Reverse;
use std::collections::{BTreeSet, HashMap, VecDeque};

use serde::{Deserialize, Serialize};

use crate::error::{TaskqError, TaskqResult};
use crate::settings::Settings;
use crate::spec::{Class, ErrorPayload, TaskEvent, TaskSpec, TaskState};

type ReadyKey = (i128, Reverse<u64>, String);
type TimedKey = (u64, u64, String);

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "kind")]
pub enum Change {
    Submitted { spec: TaskSpec },
    State { event: TaskEvent },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Submitted {
    Accepted,
    Duplicate(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Dispatch {
    pub spec: TaskSpec,
    pub attempt: u32,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct ClassCounts {
    pub queued: usize,
    pub running: usize,
}

#[derive(Debug, Clone)]
pub(crate) struct Entry {
    pub spec: TaskSpec,
    pub state: TaskState,
    pub attempt: u32,
    pub seq: u64,
    pub enqueued_at: u64,
    pub waiting: usize,
    pub error: Option<ErrorPayload>,
    pub progress: u8,
}

#[derive(Debug)]
pub struct Queue {
    pub(crate) settings: Settings,
    pub(crate) tasks: HashMap<String, Entry>,
    pub(crate) idem: HashMap<String, String>,
    pub(crate) children: HashMap<String, Vec<String>>,
    pub(crate) dependents: HashMap<String, Vec<String>>,
    pub(crate) ready: [BTreeSet<ReadyKey>; 4],
    pub(crate) delayed: BTreeSet<TimedKey>,
    pub(crate) expiry: BTreeSet<TimedKey>,
    pub(crate) terminal: VecDeque<String>,
    pub(crate) counts: [ClassCounts; 4],
    pub(crate) next_seq: u64,
    pub(crate) pending: Vec<Change>,
}

impl Queue {
    #[must_use]
    pub fn new(settings: Settings) -> Self {
        Self {
            settings,
            tasks: HashMap::new(),
            idem: HashMap::new(),
            children: HashMap::new(),
            dependents: HashMap::new(),
            ready: [const { BTreeSet::new() }; 4],
            delayed: BTreeSet::new(),
            expiry: BTreeSet::new(),
            terminal: VecDeque::new(),
            counts: [ClassCounts::default(); 4],
            next_seq: 0,
            pending: Vec::new(),
        }
    }

    pub fn drain(&mut self) -> Vec<Change> {
        std::mem::take(&mut self.pending)
    }

    #[must_use]
    pub fn counts(&self, class: Class) -> ClassCounts {
        self.counts.get(class.index()).copied().unwrap_or_default()
    }

    #[must_use]
    pub fn state(&self, id: &str) -> Option<TaskEvent> {
        self.tasks.get(id).map(|e| Self::event_of(e, Vec::new()))
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.tasks.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.tasks.is_empty()
    }

    pub(crate) fn event_of(entry: &Entry, evidence: Vec<String>) -> TaskEvent {
        TaskEvent {
            id: entry.spec.id.clone(),
            state: entry.state,
            class: entry.spec.class,
            attempt: entry.attempt,
            progress: entry.progress,
            evidence,
            error: entry.error.clone(),
        }
    }

    pub(crate) fn score(settings: &Settings, entry: &Entry) -> i128 {
        i128::from(entry.spec.priority)
            .saturating_mul(i128::from(settings.aging_ms))
            .saturating_sub(i128::from(entry.enqueued_at))
    }

    pub(crate) fn bump(&mut self, class: Class, queued: isize, running: isize) {
        if let Some(c) = self.counts.get_mut(class.index()) {
            c.queued = c.queued.saturating_add_signed(queued);
            c.running = c.running.saturating_add_signed(running);
        }
    }

    pub fn submit(&mut self, spec: TaskSpec, now: u64) -> TaskqResult<Submitted> {
        spec.validate()?;
        if let Some(existing) = spec.idem_key.as_ref().and_then(|k| self.idem.get(k)) {
            if self.tasks.get(existing).is_some_and(|e| {
                !matches!(
                    e.state,
                    TaskState::Failed | TaskState::Cancelled | TaskState::Expired
                )
            }) {
                return Ok(Submitted::Duplicate(existing.clone()));
            }
        }
        if self.tasks.contains_key(&spec.id) {
            return Err(TaskqError::Invalid);
        }
        let limits = *self.settings.limits(spec.class);
        if self.counts(spec.class).queued >= limits.capacity {
            return Err(TaskqError::Full);
        }
        if let Some(parent) = &spec.parent {
            match self.tasks.get(parent) {
                None => return Err(TaskqError::UnknownParent),
                Some(p)
                    if matches!(
                        p.state,
                        TaskState::Failed | TaskState::Cancelled | TaskState::Expired
                    ) =>
                {
                    return Err(TaskqError::DepFailed);
                }
                Some(_) => {}
            }
        }
        let mut waiting = 0usize;
        for dep in &spec.deps {
            match self.tasks.get(dep).map(|e| e.state) {
                None => return Err(TaskqError::UnknownDep),
                Some(TaskState::Done) => {}
                Some(s) if s.is_terminal() => return Err(TaskqError::DepFailed),
                Some(_) => waiting = waiting.saturating_add(1),
            }
        }
        let seq = self.next_seq;
        self.next_seq = self.next_seq.saturating_add(1);
        let entry = Entry {
            spec: spec.clone(),
            state: TaskState::Queued,
            attempt: 0,
            seq,
            enqueued_at: now,
            waiting,
            error: None,
            progress: 0,
        };
        let event = Self::event_of(&entry, Vec::new());
        self.insert_entry(entry);
        self.pending.push(Change::Submitted { spec });
        self.pending.push(Change::State { event });
        Ok(Submitted::Accepted)
    }

    pub(crate) fn insert_entry(&mut self, entry: Entry) {
        let id = entry.spec.id.clone();
        let class = entry.spec.class;
        let ttl = self.settings.limits(class).ttl_ms;
        if let Some(key) = &entry.spec.idem_key {
            self.idem.insert(key.clone(), id.clone());
        }
        if let Some(parent) = &entry.spec.parent {
            self.children
                .entry(parent.clone())
                .or_default()
                .push(id.clone());
        }
        for dep in &entry.spec.deps {
            let done = self
                .tasks
                .get(dep)
                .is_some_and(|e| e.state == TaskState::Done);
            if !done {
                self.dependents
                    .entry(dep.clone())
                    .or_default()
                    .push(id.clone());
            }
        }
        self.expiry
            .insert((entry.enqueued_at.saturating_add(ttl), entry.seq, id.clone()));
        let waiting = entry.waiting;
        self.bump(class, 1, 0);
        self.tasks.insert(id.clone(), entry);
        if waiting == 0 {
            self.make_ready(&id);
        }
    }

    pub(crate) fn make_ready(&mut self, id: &str) {
        let Some(entry) = self.tasks.get(id) else {
            return;
        };
        let key = (
            Self::score(&self.settings, entry),
            Reverse(entry.seq),
            id.to_owned(),
        );
        let class = entry.spec.class.index();
        if let Some(set) = self.ready.get_mut(class) {
            set.insert(key);
        }
    }

    pub fn tick(&mut self, now: u64) {
        while let Some(first) = self.delayed.first().cloned() {
            if first.0 > now {
                break;
            }
            self.delayed.remove(&first);
            let waiting = self
                .tasks
                .get(&first.2)
                .filter(|e| !e.state.is_terminal())
                .map(|e| e.waiting);
            if waiting == Some(0) {
                self.make_ready(&first.2);
            }
        }
        while let Some(first) = self.expiry.first().cloned() {
            if first.0 > now {
                break;
            }
            self.expiry.remove(&first);
            let queued = self
                .tasks
                .get(&first.2)
                .is_some_and(|e| matches!(e.state, TaskState::Queued | TaskState::Retrying));
            if queued {
                let err = ErrorPayload::new("taskq.expired", false);
                self.terminate(&first.2, TaskState::Expired, Some(err), Vec::new());
            }
        }
    }

    pub fn pop(&mut self, class: Class, now: u64) -> Option<Dispatch> {
        self.tick(now);
        let limits = *self.settings.limits(class);
        if self.counts(class).running >= limits.concurrency {
            return None;
        }
        let key = self.ready.get_mut(class.index())?.pop_last()?;
        let entry = self.tasks.get_mut(&key.2)?;
        entry.state = TaskState::Running;
        entry.attempt = entry.attempt.saturating_add(1);
        entry.error = None;
        let dispatch = Dispatch {
            spec: entry.spec.clone(),
            attempt: entry.attempt,
        };
        let event = Self::event_of(entry, Vec::new());
        self.bump(class, -1, 1);
        self.pending.push(Change::State { event });
        Some(dispatch)
    }

    #[must_use]
    pub fn next_wake(&self) -> Option<u64> {
        let a = self.delayed.first().map(|k| k.0);
        let b = self.expiry.first().map(|k| k.0);
        match (a, b) {
            (Some(x), Some(y)) => Some(x.min(y)),
            (x, y) => x.or(y),
        }
    }

    pub fn progress(&mut self, id: &str, percent: u8) {
        if let Some(entry) = self.tasks.get_mut(id) {
            if entry.state == TaskState::Running {
                entry.progress = percent.min(100);
            }
        }
    }
}
