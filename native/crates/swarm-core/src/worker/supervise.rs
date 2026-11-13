use std::sync::Arc;
use std::time::Duration;

use tokio::time::{Instant, sleep_until};

use super::context::{
    CODE_CANCELLED, CODE_DEADLINE, CODE_LEASE, CODE_PANIC, CancelToken, StepContext,
};
use super::factory::{Output, Worker};
use crate::wire::{Ident, WorkerError, WorkerErrorKind};

pub async fn supervise(
    worker: Arc<dyn Worker>,
    context: StepContext,
    lease_ms: u64,
    time_ms: u64,
    cancel: CancelToken,
) -> Result<Output, WorkerError> {
    let step = context.step.id.clone();
    let beat = context.beat.clone();
    beat.pulse();
    let fail = |kind, code: &'static str| WorkerError::new(kind, Ident::known(code), step.clone());
    let mut handle = tokio::spawn(async move { worker.run(context).await });
    let deadline = Instant::now()
        .checked_add(Duration::from_millis(time_ms))
        .unwrap_or_else(Instant::now);
    let mut cancelled = cancel.subscribe();
    if *cancelled.borrow() {
        handle.abort();
        return Err(fail(WorkerErrorKind::Cancelled, CODE_CANCELLED));
    }
    loop {
        tokio::select! {
            joined = &mut handle => {
                return joined.unwrap_or_else(|_| Err(fail(WorkerErrorKind::Internal, CODE_PANIC)));
            }
            () = sleep_until(deadline) => {
                handle.abort();
                return Err(fail(WorkerErrorKind::Timeout, CODE_DEADLINE));
            }
            () = sleep_until(beat.expiry(lease_ms)) => {
                if beat.idle_ms().saturating_add(1) >= lease_ms {
                    handle.abort();
                    return Err(fail(WorkerErrorKind::Timeout, CODE_LEASE));
                }
            }
            changed = cancelled.changed() => {
                if changed.is_err() || *cancelled.borrow() {
                    handle.abort();
                    return Err(fail(WorkerErrorKind::Cancelled, CODE_CANCELLED));
                }
            }
        }
    }
}
