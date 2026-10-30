use std::cmp::Reverse;
use std::collections::{BTreeMap, BTreeSet, VecDeque};

use agency_domain::{Task, TaskId, TaskSpec, TaskStatus};

use crate::error::PlanError;
use crate::progress::Progress;

pub const MAX_TASKS: usize = 2_000;

#[derive(Debug, Clone, Default)]
pub struct TaskGraph {
    tasks: BTreeMap<TaskId, Task>,
}

impl TaskGraph {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn from_specs(specs: &[TaskSpec]) -> Result<Self, PlanError> {
        let mut graph = Self::new();
        graph.extend(specs)?;
        Ok(graph)
    }

    pub fn from_tasks(tasks: Vec<Task>) -> Result<Self, PlanError> {
        let mut map = BTreeMap::new();
        for task in tasks {
            if map.contains_key(task.id()) {
                return Err(PlanError::Duplicate(task.id().clone()));
            }
            map.insert(task.id().clone(), task);
        }
        let graph = Self { tasks: map };
        graph.validate()?;
        Ok(graph)
    }

    pub fn extend(&mut self, specs: &[TaskSpec]) -> Result<(), PlanError> {
        let mut staged = self.tasks.clone();
        for spec in specs {
            let task = Task::from_spec(spec)?;
            if staged.contains_key(task.id()) {
                return Err(PlanError::Duplicate(task.id().clone()));
            }
            staged.insert(task.id().clone(), task);
        }
        let candidate = Self { tasks: staged };
        candidate.validate()?;
        *self = candidate;
        Ok(())
    }

    fn validate(&self) -> Result<(), PlanError> {
        if self.tasks.len() > MAX_TASKS {
            return Err(PlanError::TooLarge(MAX_TASKS));
        }
        for task in self.tasks.values() {
            if let Some(missing) = task
                .depends_on()
                .iter()
                .find(|d| !self.tasks.contains_key(*d))
            {
                return Err(PlanError::UnknownDependency {
                    task: task.id().clone(),
                    missing: missing.clone(),
                });
            }
        }
        if self.order().len() == self.tasks.len() {
            Ok(())
        } else {
            Err(PlanError::Cycle)
        }
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.tasks.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.tasks.is_empty()
    }

    #[must_use]
    pub fn get(&self, id: &TaskId) -> Option<&Task> {
        self.tasks.get(id)
    }

    pub fn tasks(&self) -> impl Iterator<Item = &Task> {
        self.tasks.values()
    }

    pub fn update<F>(&mut self, id: &TaskId, change: F) -> Result<(), PlanError>
    where
        F: FnOnce(&mut Task) -> Result<(), agency_domain::DomainError>,
    {
        let task = self
            .tasks
            .get_mut(id)
            .ok_or_else(|| PlanError::NotFound(id.clone()))?;
        change(task).map_err(PlanError::from)
    }

    pub fn remove(&mut self, id: &TaskId) -> Result<Task, PlanError> {
        let task = self
            .tasks
            .get(id)
            .ok_or_else(|| PlanError::NotFound(id.clone()))?;
        let has_dependents = self.tasks.values().any(|t| t.depends_on().contains(id));
        if task.status() != TaskStatus::Pending || has_dependents {
            return Err(PlanError::NotRemovable(id.clone()));
        }
        self.tasks
            .remove(id)
            .ok_or_else(|| PlanError::NotFound(id.clone()))
    }

    fn dependents(&self) -> BTreeMap<&TaskId, Vec<&TaskId>> {
        let mut map: BTreeMap<&TaskId, Vec<&TaskId>> =
            self.tasks.keys().map(|k| (k, Vec::new())).collect();
        for task in self.tasks.values() {
            for dep in task.depends_on() {
                if let Some(list) = map.get_mut(dep) {
                    list.push(task.id());
                }
            }
        }
        map
    }

    #[must_use]
    pub fn order(&self) -> Vec<&TaskId> {
        let dependents = self.dependents();
        let mut indegree: BTreeMap<&TaskId, usize> = self
            .tasks
            .values()
            .map(|t| (t.id(), t.depends_on().len()))
            .collect();
        let mut queue: VecDeque<&TaskId> = indegree
            .iter()
            .filter(|(_, n)| **n == 0)
            .map(|(id, _)| *id)
            .collect();
        let mut out = Vec::with_capacity(self.tasks.len());
        while let Some(id) = queue.pop_front() {
            out.push(id);
            for next in dependents.get(id).into_iter().flatten() {
                if let Some(n) = indegree.get_mut(*next) {
                    *n = n.saturating_sub(1);
                    if *n == 0 {
                        queue.push_back(*next);
                    }
                }
            }
        }
        out
    }

    fn remaining_tail(&self) -> BTreeMap<&TaskId, u64> {
        let dependents = self.dependents();
        let mut tail: BTreeMap<&TaskId, u64> = BTreeMap::new();
        for id in self.order().into_iter().rev() {
            let own = self
                .tasks
                .get(id)
                .filter(|t| !t.status().is_terminal())
                .map_or(0, Task::estimate_seconds);
            let longest = dependents
                .get(id)
                .into_iter()
                .flatten()
                .filter_map(|d| tail.get(*d).copied())
                .max()
                .unwrap_or(0);
            tail.insert(id, own.saturating_add(longest));
        }
        tail
    }

    #[must_use]
    pub fn critical_path_seconds(&self) -> u64 {
        self.remaining_tail().values().copied().max().unwrap_or(0)
    }

    fn deps_done(&self, task: &Task) -> bool {
        task.depends_on().iter().all(|d| {
            self.tasks
                .get(d)
                .is_some_and(|t| t.status() == TaskStatus::Done)
        })
    }

    #[must_use]
    pub fn ready(&self) -> Vec<&TaskId> {
        let tail = self.remaining_tail();
        let mut ready: Vec<&TaskId> = self
            .tasks
            .values()
            .filter(|t| t.status() == TaskStatus::Pending && self.deps_done(t))
            .map(Task::id)
            .collect();
        ready.sort_by_key(|id| (Reverse(tail.get(id).copied().unwrap_or(0)), *id));
        ready
    }

    #[must_use]
    pub fn dispatchable(&self, parallel_limit: usize) -> Vec<&TaskId> {
        let busy = self
            .tasks
            .values()
            .filter(|t| t.status() == TaskStatus::Running)
            .count();
        let room = parallel_limit.saturating_sub(busy);
        self.ready().into_iter().take(room).collect()
    }

    #[must_use]
    pub fn blocked(&self) -> BTreeSet<&TaskId> {
        let mut blocked = BTreeSet::new();
        for id in self.order() {
            let Some(task) = self.tasks.get(id) else {
                continue;
            };
            if task.status().is_terminal() {
                continue;
            }
            let stuck = task.depends_on().iter().any(|d| {
                blocked.contains(d)
                    || self.tasks.get(d).is_some_and(|t| {
                        matches!(t.status(), TaskStatus::Failed | TaskStatus::Cancelled)
                    })
            });
            if stuck {
                blocked.insert(id);
            }
        }
        blocked
    }

    #[must_use]
    pub fn is_finished(&self) -> bool {
        let blocked = self.blocked();
        self.tasks
            .values()
            .all(|t| t.status().is_terminal() || blocked.contains(t.id()))
    }

    #[must_use]
    pub fn progress(&self) -> Progress {
        let mut p = Progress {
            total: self.tasks.len(),
            blocked: self.blocked().len(),
            ..Progress::default()
        };
        for task in self.tasks.values() {
            let slot = match task.status() {
                TaskStatus::Pending => &mut p.pending,
                TaskStatus::Running => &mut p.running,
                TaskStatus::Review => &mut p.review,
                TaskStatus::Done => &mut p.done,
                TaskStatus::Failed => &mut p.failed,
                TaskStatus::Cancelled => &mut p.cancelled,
            };
            *slot = slot.saturating_add(1);
        }
        p.finish()
    }
}
