use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU8, Ordering};

use tokio::sync::Notify;

#[derive(Debug, Clone)]
pub struct CancelToken {
    inner: Arc<TokenInner>,
}

#[derive(Debug)]
struct TokenInner {
    flag: AtomicBool,
    notify: Notify,
}

impl Default for CancelToken {
    fn default() -> Self {
        Self::new()
    }
}

impl CancelToken {
    #[must_use]
    pub fn new() -> Self {
        Self {
            inner: Arc::new(TokenInner {
                flag: AtomicBool::new(false),
                notify: Notify::new(),
            }),
        }
    }

    pub fn cancel(&self) {
        self.inner.flag.store(true, Ordering::SeqCst);
        self.inner.notify.notify_waiters();
    }

    #[must_use]
    pub fn is_cancelled(&self) -> bool {
        self.inner.flag.load(Ordering::SeqCst)
    }

    pub async fn cancelled(&self) {
        loop {
            let waiter = self.inner.notify.notified();
            if self.is_cancelled() {
                return;
            }
            waiter.await;
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct Progress {
    value: Arc<AtomicU8>,
}

impl Progress {
    pub fn set(&self, percent: u8) {
        self.value.store(percent.min(100), Ordering::Relaxed);
    }

    #[must_use]
    pub fn get(&self) -> u8 {
        self.value.load(Ordering::Relaxed)
    }
}
