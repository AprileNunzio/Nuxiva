use super::{Change, Queue};
use crate::error::{TaskqError, TaskqResult};
use crate::spec::{Class, ErrorPayload, TaskEvent, TaskState};

const CODE_DEP: &str = "taskq.dep_failed";
const CODE_CANCELLED: &str = "taskq.cancelled";

fn mix(id: &str, attempt: u32) -> u64 {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for byte in id.bytes().chain(attempt.to_le_bytes()) {
        hash ^= u64::from(byte);
        hash = hash.wrapping_mul(0x0100_0000_01b3);
    }
    hash
}

impl Queue {
    pub(crate) fn backoff(&self, id: &str, attempt: u32) -> u64 {
        let shift = attempt.saturating_sub(1).min(32);
        let raw = self
            .settings
            .backoff_base_ms
            .saturating_mul(1u64.checked_shl(shift).unwrap_or(u64::MAX))
            .min(self.settings.backoff_cap_ms);
        let span = raw.checked_div(4).unwrap_or(0);
        let jitter = mix(id, attempt)
            .checked_rem(span.saturating_add(1))
            .unwrap_or(0);
        raw.saturating_add(jitter).min(self.settings.backoff_cap_ms)
    }

    pub fn complete(
        &mut self,
        id: &str,
        evidence: Vec<String>,
        now: u64,
    ) -> TaskqResult<Vec<String>> {
        self.require_running(id)?;
        let _ = now;
        let signals = self.terminate(id, TaskState::Done, None, evidence);
        Ok(signals)
    }

    pub fn fail(&mut self, id: &str, error: ErrorPayload, now: u64) -> TaskqResult<Vec<String>> {
        let (class, attempt) = self.require_running(id)?;
        let max = self.settings.limits(class).max_retries;
        if error.transient && attempt <= max {
            let ready_at = now.saturating_add(self.backoff(id, attempt));
            let Some(entry) = self.tasks.get_mut(id) else {
                return Err(TaskqError::NotFound);
            };
            entry.state = TaskState::Retrying;
            entry.error = Some(error);
            let seq = entry.seq;
            let event = Self::event_of(entry, Vec::new());
            self.bump(class, 1, -1);
            self.delayed.insert((ready_at, seq, id.to_owned()));
            self.pending.push(Change::State { event });
            return Ok(Vec::new());
        }
        Ok(self.terminate(id, TaskState::Failed, Some(error), Vec::new()))
    }

    pub fn cancel(&mut self, id: &str) -> TaskqResult<Vec<String>> {
        match self.tasks.get(id) {
            None => Err(TaskqError::NotFound),
            Some(e) if e.state.is_terminal() => Err(TaskqError::Terminal),
            Some(_) => Ok(self.terminate(
                id,
                TaskState::Cancelled,
                Some(ErrorPayload::new(CODE_CANCELLED, false)),
                Vec::new(),
            )),
        }
    }

    fn require_running(&self, id: &str) -> TaskqResult<(Class, u32)> {
        match self.tasks.get(id) {
            None => Err(TaskqError::NotFound),
            Some(e) if e.state == TaskState::Running => Ok((e.spec.class, e.attempt)),
            Some(_) => Err(TaskqError::Terminal),
        }
    }

    pub(crate) fn terminate(
        &mut self,
        id: &str,
        state: TaskState,
        error: Option<ErrorPayload>,
        evidence: Vec<String>,
    ) -> Vec<String> {
        let mut signals = Vec::new();
        let mut stack = vec![(id.to_owned(), state, error, evidence)];
        while let Some((current, state, error, evidence)) = stack.pop() {
            let Some(entry) = self.tasks.get_mut(&current) else {
                continue;
            };
            if entry.state.is_terminal() {
                continue;
            }
            let was = entry.state;
            let class = entry.spec.class;
            let seq = entry.seq;
            let score_key = (
                Self::score(&self.settings, entry),
                std::cmp::Reverse(seq),
                current.clone(),
            );
            entry.state = state;
            entry.error = error;
            if state == TaskState::Done {
                entry.progress = 100;
            }
            let event = Self::event_of(entry, evidence);
            if was == TaskState::Running {
                self.bump(class, 0, -1);
                if matches!(state, TaskState::Cancelled | TaskState::Expired) {
                    signals.push(current.clone());
                }
            } else {
                self.bump(class, -1, 0);
                if let Some(set) = self.ready.get_mut(class.index()) {
                    set.remove(&score_key);
                }
            }
            self.pending.push(Change::State { event });
            self.remember_terminal(&current);
            self.cascade(&current, state, &mut stack);
        }
        self.evict();
        signals
    }

    fn cascade(
        &mut self,
        id: &str,
        state: TaskState,
        stack: &mut Vec<(String, TaskState, Option<ErrorPayload>, Vec<String>)>,
    ) {
        let dependents = self.dependents.remove(id).unwrap_or_default();
        if state == TaskState::Done {
            for dep in dependents {
                let release = match self.tasks.get_mut(&dep) {
                    Some(e) if !e.state.is_terminal() => {
                        e.waiting = e.waiting.saturating_sub(1);
                        e.waiting == 0 && e.state == TaskState::Queued
                    }
                    _ => false,
                };
                if release {
                    self.make_ready(&dep);
                }
            }
            return;
        }
        for dep in dependents {
            stack.push((
                dep,
                TaskState::Cancelled,
                Some(ErrorPayload::new(CODE_DEP, false)),
                Vec::new(),
            ));
        }
        for child in self.children.remove(id).unwrap_or_default() {
            stack.push((
                child,
                TaskState::Cancelled,
                Some(ErrorPayload::new(CODE_CANCELLED, false)),
                Vec::new(),
            ));
        }
    }

    fn remember_terminal(&mut self, id: &str) {
        self.terminal.push_back(id.to_owned());
    }

    fn evict(&mut self) {
        while self.terminal.len() > self.settings.retain_terminal {
            let Some(id) = self.terminal.pop_front() else {
                break;
            };
            let Some(entry) = self.tasks.remove(&id) else {
                continue;
            };
            if let Some(key) = &entry.spec.idem_key {
                if self.idem.get(key) == Some(&id) {
                    self.idem.remove(key);
                }
            }
            if let Some(parent) = &entry.spec.parent {
                if let Some(list) = self.children.get_mut(parent) {
                    list.retain(|c| c != &id);
                }
            }
        }
    }

    #[must_use]
    pub fn snapshot(&self, id: &str) -> Option<TaskEvent> {
        self.state(id)
    }
}
