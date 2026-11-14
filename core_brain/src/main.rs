use std::process::ExitCode;
use std::sync::Arc;

use core_brain::{
    BrainError, Embedder, Event, Gatekeeper, HotMemory, SensoryPipeline, SharedPipeline,
    Supervisor, SupervisorConfig,
};
use nuxiva_context_core::{ContextSettings, Sealer, SharedContext};
use nuxiva_ear_core::VoicePolicy;

struct Unbound;

impl Embedder for Unbound {
    fn embed(&self, _pcm: &[f32]) -> Result<Vec<f32>, BrainError> {
        Err(BrainError::Embedding("unbound"))
    }
}

#[tokio::main]
async fn main() -> ExitCode {
    let built = Sealer::random()
        .and_then(|sealer| SharedContext::new(ContextSettings::default(), sealer))
        .map_err(BrainError::from);
    let shared = match built {
        Ok(shared) => shared,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let memory = HotMemory::new(shared);
    let pipeline = SharedPipeline::new(SensoryPipeline::new(
        Arc::new(Unbound),
        Gatekeeper::new(["nuxiva"]),
        VoicePolicy::default(),
    ));
    let (supervisor, mut events) = Supervisor::start(pipeline, memory, SupervisorConfig::default());
    let drain = tokio::spawn(async move {
        while let Some(event) = events.recv().await {
            if let Event::Fault(error) = event {
                eprintln!("{error}");
            }
        }
    });
    if let Err(error) = tokio::signal::ctrl_c().await {
        eprintln!("{error}");
    }
    let status = supervisor.shutdown().await;
    let _ = drain.await;
    match status {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
