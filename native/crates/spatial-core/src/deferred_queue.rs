use crate::priority::NotificationEvent;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

pub const MAX_DEFERRED_EVENTS: usize = 64;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct DeferredQueue {
    queue: VecDeque<NotificationEvent>,
}

impl DeferredQueue {
    #[must_use]
    pub fn new() -> Self {
        Self {
            queue: VecDeque::with_capacity(MAX_DEFERRED_EVENTS),
        }
    }

    pub fn push(&mut self, event: NotificationEvent) {
        if self.queue.len() >= MAX_DEFERRED_EVENTS {
            let _ = self.queue.pop_front();
        }
        self.queue.push_back(event);
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.queue.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }

    #[must_use]
    pub fn events(&self) -> &VecDeque<NotificationEvent> {
        &self.queue
    }

    pub fn drain_all(&mut self) -> Vec<NotificationEvent> {
        self.queue.drain(..).collect()
    }
}
