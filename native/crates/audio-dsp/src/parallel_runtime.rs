use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PipelineTaskStatus {
    Pending,
    Processing,
    Completed,
    Dropped,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PipelineTask<T> {
    pub task_id: u64,
    pub status: PipelineTaskStatus,
    pub payload: T,
}

impl<T> PipelineTask<T> {
    #[must_use]
    pub const fn new(task_id: u64, payload: T) -> Self {
        Self {
            task_id,
            status: PipelineTaskStatus::Pending,
            payload,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct ConcurrentAudioPipeline<T> {
    incoming_queue: VecDeque<PipelineTask<T>>,
    completed_queue: VecDeque<PipelineTask<T>>,
    max_capacity: usize,
    next_task_id: u64,
}

impl<T> Default for ConcurrentAudioPipeline<T> {
    fn default() -> Self {
        Self::new(128)
    }
}

impl<T> ConcurrentAudioPipeline<T> {
    #[must_use]
    pub fn new(max_capacity: usize) -> Self {
        Self {
            incoming_queue: VecDeque::with_capacity(max_capacity),
            completed_queue: VecDeque::with_capacity(max_capacity),
            max_capacity,
            next_task_id: 1,
        }
    }

    pub fn submit(&mut self, payload: T) -> u64 {
        let task_id = self.next_task_id;
        self.next_task_id = self.next_task_id.saturating_add(1);

        if self.incoming_queue.len() >= self.max_capacity {
            let _ = self.incoming_queue.pop_front();
        }

        self.incoming_queue
            .push_back(PipelineTask::new(task_id, payload));
        task_id
    }

    pub fn pop_pending(&mut self) -> Option<PipelineTask<T>> {
        self.incoming_queue.pop_front()
    }

    pub fn push_completed(&mut self, mut task: PipelineTask<T>) {
        task.status = PipelineTaskStatus::Completed;
        if self.completed_queue.len() >= self.max_capacity {
            let _ = self.completed_queue.pop_front();
        }
        self.completed_queue.push_back(task);
    }

    pub fn drain_completed(&mut self) -> Vec<PipelineTask<T>> {
        self.completed_queue.drain(..).collect()
    }

    #[must_use]
    pub fn pending_count(&self) -> usize {
        self.incoming_queue.len()
    }

    #[must_use]
    pub fn completed_count(&self) -> usize {
        self.completed_queue.len()
    }
}
