use std::time::Duration;

use nuxiva_context_core::PersonId;
use tokio::sync::{mpsc, watch};
use tokio::task::JoinHandle;
use tokio::time::timeout;

use crate::error::{BrainError, BrainResult};
use crate::memory::HotMemory;
use crate::sensory::{Decision, Frame, Layer, SharedPipeline};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SupervisorConfig {
    pub input_queue: usize,
    pub event_queue: usize,
    pub frame_deadline: Duration,
}

impl Default for SupervisorConfig {
    fn default() -> Self {
        Self {
            input_queue: 64,
            event_queue: 64,
            frame_deadline: Duration::from_millis(750),
        }
    }
}

impl SupervisorConfig {
    #[must_use]
    pub fn sanitized(self) -> Self {
        Self {
            input_queue: self.input_queue.clamp(1, 4_096),
            event_queue: self.event_queue.clamp(1, 4_096),
            frame_deadline: self
                .frame_deadline
                .clamp(Duration::from_millis(10), Duration::from_secs(30)),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum Event {
    Heard {
        speaker: Option<String>,
        text: String,
        score: f32,
        at_ms: u64,
    },
    Dropped {
        layer: Layer,
        reason: &'static str,
    },
    Fault(BrainError),
}

#[derive(Debug)]
pub struct Supervisor {
    input: mpsc::Sender<Frame>,
    stop: watch::Sender<bool>,
    task: JoinHandle<()>,
}

impl Supervisor {
    #[must_use]
    pub fn start(
        pipeline: SharedPipeline,
        memory: HotMemory,
        config: SupervisorConfig,
    ) -> (Self, mpsc::Receiver<Event>) {
        let config = config.sanitized();
        let (input, frames) = mpsc::channel(config.input_queue);
        let (events_tx, events) = mpsc::channel(config.event_queue);
        let (stop, stopped) = watch::channel(false);
        let task = tokio::spawn(run(pipeline, memory, config, frames, events_tx, stopped));
        (Self { input, stop, task }, events)
    }

    pub fn submit(&self, frame: Frame) -> BrainResult<()> {
        frame.validate()?;
        self.input.try_send(frame).map_err(|e| match e {
            mpsc::error::TrySendError::Full(_) => BrainError::QueueFull,
            mpsc::error::TrySendError::Closed(_) => BrainError::Closed,
        })
    }

    pub async fn shutdown(self) -> BrainResult<()> {
        let _ = self.stop.send(true);
        self.task.await.map_err(|_| BrainError::Panic)
    }
}

async fn run(
    pipeline: SharedPipeline,
    memory: HotMemory,
    config: SupervisorConfig,
    mut frames: mpsc::Receiver<Frame>,
    events: mpsc::Sender<Event>,
    mut stopped: watch::Receiver<bool>,
) {
    loop {
        let frame = tokio::select! {
            biased;
            _ = stopped.changed() => break,
            next = frames.recv() => match next {
                Some(frame) => frame,
                None => break,
            },
        };
        let event = handle(&pipeline, &memory, config, frame).await;
        if events.send(event).await.is_err() {
            break;
        }
    }
}

async fn handle(
    pipeline: &SharedPipeline,
    memory: &HotMemory,
    config: SupervisorConfig,
    frame: Frame,
) -> Event {
    let worker = pipeline.clone();
    let at_ms = frame.at_ms;
    let job = tokio::task::spawn_blocking(move || worker.process(&frame));
    let outcome = match timeout(config.frame_deadline, job).await {
        Err(_) => return Event::Fault(BrainError::Deadline),
        Ok(Err(_)) => return Event::Fault(BrainError::Panic),
        Ok(Ok(result)) => result,
    };
    match outcome {
        Err(error) => Event::Fault(error),
        Ok(Decision::Rejected { layer, reason }) => Event::Dropped { layer, reason },
        Ok(Decision::Accepted {
            speaker,
            text,
            score,
            ..
        }) => {
            let id = match speaker.as_deref().map(PersonId::new).transpose() {
                Ok(id) => id,
                Err(error) => return Event::Fault(error.into()),
            };
            memory.register_turn(id, at_ms).await;
            Event::Heard {
                speaker,
                text,
                score,
                at_ms,
            }
        }
    }
}
