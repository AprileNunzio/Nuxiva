use std::collections::HashMap;

use super::{Change, Entry, Queue};
use crate::error::{TaskqError, TaskqResult};
use crate::settings::Settings;
use crate::spec::{ErrorPayload, Risk, TaskState};

const CODE_INTERRUPTED: &str = "taskq.interrupted";

impl Queue {
    pub fn restore(settings: Settings, changes: Vec<Change>, now: u64) -> TaskqResult<Self> {
        let mut queue = Self::new(settings);
        let mut staged: HashMap<String, Entry> = HashMap::new();
        let mut order: Vec<String> = Vec::new();
        for change in changes {
            match change {
                Change::Submitted { spec } => {
                    spec.validate()?;
                    if staged.contains_key(&spec.id) {
                        return Err(TaskqError::Tamper);
                    }
                    let seq = queue.next_seq;
                    queue.next_seq = queue.next_seq.saturating_add(1);
                    order.push(spec.id.clone());
                    staged.insert(
                        spec.id.clone(),
                        Entry {
                            spec,
                            state: TaskState::Queued,
                            attempt: 0,
                            seq,
                            enqueued_at: now,
                            waiting: 0,
                            error: None,
                            progress: 0,
                        },
                    );
                }
                Change::State { event } => {
                    let entry = staged.get_mut(&event.id).ok_or(TaskqError::Tamper)?;
                    entry.state = event.state;
                    entry.attempt = event.attempt;
                    entry.error = event.error;
                    entry.progress = event.progress;
                }
            }
        }
        for id in order {
            let Some(mut entry) = staged.remove(&id) else {
                continue;
            };
            if entry.state.is_terminal() {
                queue.restore_terminal(entry);
                continue;
            }
            let interrupted = entry.state == TaskState::Running;
            if interrupted && entry.spec.risk_max >= Risk::High {
                entry.state = TaskState::Failed;
                entry.error = Some(ErrorPayload::new(CODE_INTERRUPTED, false));
                let event = Self::event_of(&entry, Vec::new());
                queue.restore_terminal(entry);
                queue.pending.push(Change::State { event });
                continue;
            }
            entry.state = TaskState::Queued;
            entry.waiting = entry
                .spec
                .deps
                .iter()
                .filter(|d| {
                    !queue
                        .tasks
                        .get(*d)
                        .is_some_and(|e| e.state == TaskState::Done)
                })
                .count();
            let blocked = entry.spec.deps.iter().any(|d| {
                queue
                    .tasks
                    .get(d)
                    .is_none_or(|e| e.state.is_terminal() && e.state != TaskState::Done)
            });
            let id = entry.spec.id.clone();
            queue.insert_entry(entry);
            if blocked {
                queue.terminate(
                    &id,
                    TaskState::Cancelled,
                    Some(ErrorPayload::new("taskq.dep_failed", false)),
                    Vec::new(),
                );
            } else if interrupted {
                if let Some(e) = queue.tasks.get(&id) {
                    let event = Self::event_of(e, Vec::new());
                    queue.pending.push(Change::State { event });
                }
            }
        }
        Ok(queue)
    }

    fn restore_terminal(&mut self, entry: Entry) {
        let id = entry.spec.id.clone();
        if let Some(key) = &entry.spec.idem_key {
            self.idem.insert(key.clone(), id.clone());
        }
        self.tasks.insert(id.clone(), entry);
        self.terminal.push_back(id);
    }
}

impl Queue {
    #[must_use]
    pub fn compact_changes(&self) -> Vec<Change> {
        let mut entries: Vec<&Entry> = self.tasks.values().collect();
        entries.sort_by_key(|e| e.seq);
        let mut out = Vec::with_capacity(entries.len().saturating_mul(2));
        for entry in entries {
            out.push(Change::Submitted {
                spec: entry.spec.clone(),
            });
            out.push(Change::State {
                event: Self::event_of(entry, Vec::new()),
            });
        }
        out
    }
}
