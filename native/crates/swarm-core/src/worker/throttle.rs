use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use tokio::sync::{Semaphore, SemaphorePermit};

use super::context::CancelToken;
use crate::budget::ResourceBudget;

const POLL: Duration = Duration::from_millis(5);

#[derive(Debug)]
pub(super) struct Throttle {
    slots: Semaphore,
    active: AtomicUsize,
    ceiling: usize,
    budget: Arc<dyn ResourceBudget>,
}

pub(super) struct Slot<'a> {
    throttle: &'a Throttle,
    _permit: SemaphorePermit<'a>,
}

impl Drop for Slot<'_> {
    fn drop(&mut self) {
        self.throttle.active.fetch_sub(1, Ordering::AcqRel);
    }
}

impl Throttle {
    pub(super) fn new(ceiling: usize, budget: Arc<dyn ResourceBudget>) -> Self {
        let ceiling = ceiling.max(1);
        Self {
            slots: Semaphore::new(ceiling),
            active: AtomicUsize::new(0),
            ceiling,
            budget,
        }
    }

    pub(super) async fn acquire(&self, cancel: &CancelToken) -> Option<Slot<'_>> {
        loop {
            let permit = self.slots.acquire().await.ok()?;
            let cap = self.budget.workers().clamp(1, self.ceiling);
            let reserved = self
                .active
                .try_update(Ordering::AcqRel, Ordering::Acquire, |now| {
                    now.checked_add(1).filter(|next| *next <= cap)
                })
                .is_ok();
            if reserved {
                return Some(Slot {
                    throttle: self,
                    _permit: permit,
                });
            }
            drop(permit);
            if cancel.is_cancelled() {
                return None;
            }
            tokio::time::sleep(POLL).await;
        }
    }
}
