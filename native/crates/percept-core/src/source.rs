use std::collections::VecDeque;
use std::sync::{Mutex, PoisonError};

use crate::error::{PerceptError, PerceptResult};
use crate::observation::Observation;

pub trait PerceptSource: Send + Sync {
    fn drain(&self) -> Vec<Observation>;
}

#[derive(Debug)]
pub struct QueueSource {
    capacity: usize,
    queue: Mutex<VecDeque<Observation>>,
}

impl QueueSource {
    #[must_use]
    pub fn new(capacity: usize) -> Self {
        Self {
            capacity: capacity.max(1),
            queue: Mutex::new(VecDeque::new()),
        }
    }

    pub fn push(&self, observation: Observation) {
        let mut queue = self.queue.lock().unwrap_or_else(PoisonError::into_inner);
        while queue.len() >= self.capacity {
            queue.pop_front();
        }
        queue.push_back(observation);
    }

    pub fn push_json(&self, raw: &str) -> PerceptResult<()> {
        let observation: Observation =
            serde_json::from_str(raw).map_err(|_| PerceptError::Invalid)?;
        self.push(observation);
        Ok(())
    }
}

impl PerceptSource for QueueSource {
    fn drain(&self) -> Vec<Observation> {
        let mut queue = self.queue.lock().unwrap_or_else(PoisonError::into_inner);
        queue.drain(..).collect()
    }
}
