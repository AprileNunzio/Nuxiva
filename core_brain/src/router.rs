use std::sync::Arc;

use tokio::sync::{Semaphore, mpsc};
use tokio::task::JoinSet;

use crate::dispatch::{Dispatched, Dispatcher};
use crate::error::BrainError;
use crate::sensory::Layer;
use crate::supervisor::Event;

const MAX_CONCURRENT: usize = 4;
const GUEST: &str = "guest";

#[derive(Debug, Clone, PartialEq)]
pub enum Outcome {
    Done(Dispatched),
    Failed(BrainError),
    Dropped { layer: Layer, reason: &'static str },
}

pub async fn route(
    mut events: mpsc::Receiver<Event>,
    dispatcher: Arc<Dispatcher>,
    outcomes: mpsc::Sender<Outcome>,
) {
    let gate = Arc::new(Semaphore::new(MAX_CONCURRENT));
    let mut jobs: JoinSet<()> = JoinSet::new();
    while let Some(event) = events.recv().await {
        match event {
            Event::Dropped { layer, reason } => {
                if outcomes
                    .send(Outcome::Dropped { layer, reason })
                    .await
                    .is_err()
                {
                    break;
                }
            }
            Event::Fault(error) => {
                if outcomes.send(Outcome::Failed(error)).await.is_err() {
                    break;
                }
            }
            Event::Heard {
                speaker,
                text,
                at_ms,
                ..
            } => {
                let Ok(permit) = Arc::clone(&gate).acquire_owned().await else {
                    break;
                };
                let dispatcher = Arc::clone(&dispatcher);
                let outcomes = outcomes.clone();
                jobs.spawn(async move {
                    let principal = speaker.as_deref().unwrap_or(GUEST);
                    let outcome = match dispatcher.dispatch(&text, principal, at_ms).await {
                        Ok(done) => Outcome::Done(done),
                        Err(error) => Outcome::Failed(error),
                    };
                    let _ = outcomes.send(outcome).await;
                    drop(permit);
                });
            }
        }
        while jobs.try_join_next().is_some() {}
    }
    dispatcher.cancel_all();
    while jobs.join_next().await.is_some() {}
}
