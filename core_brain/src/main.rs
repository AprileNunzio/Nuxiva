use std::path::PathBuf;
use std::process::ExitCode;
use std::sync::Arc;

use core_brain::{
    BrainError, BrainResult, Dispatcher, Gatekeeper, HotMemory, OnnxEmbedder, Outcome,
    SPEAKER_MODEL, SensoryPipeline, SharedPipeline, Supervisor, SupervisorConfig, route,
};
use nuxiva_agent_core::ceo::Index;
use nuxiva_context_core::{ContextSettings, Sealer, SharedContext};
use nuxiva_ear_core::VoicePolicy;
use nuxiva_mcp_core::{Hub, MemorySink, PolicyConfig, Settings as McpSettings, SharedSecrets};
use nuxiva_swarm_core::{Catalog, Settings as SwarmSettings};
use tokio::sync::mpsc;

fn model_dir() -> PathBuf {
    std::env::var_os("NUXIVA_MODEL_DIR")
        .map_or_else(|| PathBuf::from("core_brain_models"), PathBuf::from)
}

fn wake_names() -> Vec<String> {
    std::env::var("NUXIVA_WAKE_NAMES")
        .ok()
        .map(|v| {
            v.split(',')
                .map(str::trim)
                .filter(|n| !n.is_empty())
                .map(str::to_owned)
                .collect()
        })
        .filter(|v: &Vec<String>| !v.is_empty())
        .unwrap_or_else(|| vec!["nuxiva".to_owned()])
}

async fn assemble() -> BrainResult<(
    Supervisor,
    mpsc::Receiver<core_brain::Event>,
    Arc<Dispatcher>,
)> {
    let sealer = Sealer::random()?;
    let memory = HotMemory::new(SharedContext::new(ContextSettings::default(), sealer)?);
    let data = SPEAKER_MODEL.fetch(&model_dir()).await?;
    let embedder =
        tokio::task::spawn_blocking(move || OnnxEmbedder::from_verified(&SPEAKER_MODEL, &data))
            .await
            .map_err(|_| BrainError::Panic)??;
    let pipeline = SharedPipeline::new(SensoryPipeline::new(
        Arc::new(embedder),
        Gatekeeper::new(wake_names()),
        VoicePolicy::default(),
    ));
    let swarm_settings = SwarmSettings::default();
    let catalog =
        Catalog::build(&[], &swarm_settings).map_err(|e| BrainError::Dispatch(e.to_string()))?;
    let hub = Hub::new(
        McpSettings::default(),
        PolicyConfig::default(),
        Arc::new(SharedSecrets::default()),
        Box::new(MemorySink::default()),
        None,
    )
    .map_err(|e| BrainError::Dispatch(e.to_string()))?;
    let dispatcher = Arc::new(Dispatcher::new(
        catalog,
        swarm_settings,
        Index::new(Vec::new()),
        Arc::new(hub),
    )?);
    let (supervisor, events) = Supervisor::start(pipeline, memory, SupervisorConfig::default());
    Ok((supervisor, events, dispatcher))
}

#[tokio::main]
async fn main() -> ExitCode {
    let (supervisor, events, dispatcher) = match assemble().await {
        Ok(parts) => parts,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let (out_tx, mut out_rx) = mpsc::channel(64);
    let router = tokio::spawn(route(events, dispatcher, out_tx));
    let drain = tokio::spawn(async move {
        while let Some(outcome) = out_rx.recv().await {
            if let Outcome::Failed(error) = outcome {
                eprintln!("{error}");
            }
        }
    });
    if let Err(error) = tokio::signal::ctrl_c().await {
        eprintln!("{error}");
    }
    let status = supervisor.shutdown().await;
    let _ = router.await;
    let _ = drain.await;
    match status {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            ExitCode::FAILURE
        }
    }
}
