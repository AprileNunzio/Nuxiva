use std::collections::VecDeque;
use std::future::Future;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, PoisonError};
use std::time::{SystemTime, UNIX_EPOCH};

use sha2::{Digest, Sha256};
use tokio::task::{AbortHandle, JoinHandle};

use crate::payload::{ErrorPayload, SCHEMA_VERSION};

#[derive(Debug)]
pub struct ErrorBus {
    queue: Mutex<VecDeque<ErrorPayload>>,
    capacity: usize,
    dropped: AtomicU64,
}

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| u64::try_from(d.as_millis()).unwrap_or(u64::MAX))
}

fn digest(parts: &[&str]) -> String {
    let mut hasher = Sha256::new();
    for part in parts {
        hasher.update(part.as_bytes());
        hasher.update([0]);
    }
    hasher
        .finalize()
        .iter()
        .flat_map(|b| [b >> 4, b & 15])
        .filter_map(|n| char::from_digit(u32::from(n), 16))
        .collect()
}

impl ErrorBus {
    #[must_use]
    pub fn new(capacity: usize) -> Self {
        Self {
            queue: Mutex::new(VecDeque::new()),
            capacity: capacity.max(1),
            dropped: AtomicU64::new(0),
        }
    }

    pub fn report(&self, component: &str, code: &str, context: &str) {
        let payload = ErrorPayload {
            schema_version: SCHEMA_VERSION,
            component: component.chars().take(128).collect(),
            code: code.chars().take(128).collect(),
            context: context.chars().take(256).collect(),
            hash: digest(&[component, code, context]),
            at_ms: now_ms(),
        };
        let mut queue = self.queue.lock().unwrap_or_else(PoisonError::into_inner);
        if queue.len() >= self.capacity {
            queue.pop_front();
            self.dropped.fetch_add(1, Ordering::Relaxed);
        }
        queue.push_back(payload);
    }

    pub fn drain(&self) -> Vec<ErrorPayload> {
        self.queue
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .drain(..)
            .collect()
    }

    #[must_use]
    pub fn dropped(&self) -> u64 {
        self.dropped.load(Ordering::Relaxed)
    }
}

struct AbortOnDrop(AbortHandle);

impl Drop for AbortOnDrop {
    fn drop(&mut self) {
        self.0.abort();
    }
}

pub fn guarded<F>(
    bus: Arc<ErrorBus>,
    component: String,
    context: String,
    future: F,
) -> JoinHandle<()>
where
    F: Future<Output = ()> + Send + 'static,
{
    tokio::spawn(async move {
        let inner = tokio::spawn(future);
        let _abort = AbortOnDrop(inner.abort_handle());
        if let Err(error) = inner.await {
            if error.is_panic() {
                bus.report(&component, "panic", &context);
            }
        }
    })
}
