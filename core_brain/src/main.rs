use std::path::PathBuf;
use std::process::ExitCode;
use std::sync::Arc;

use core_brain::{
    BrainError, BrainResult, Dispatcher, EarEndpoint, Event, Gatekeeper, HotMemory, OnnxEmbedder,
    Outcome, Paths, SPEAKER_MODEL, SensoryPipeline, SharedPipeline, Supervisor, SupervisorConfig,
    build_hub, load_agents, route, run_ear,
};
use nuxiva_context_core::{ContextSettings, Sealer, SharedContext};
use nuxiva_ear_core::VoicePolicy;
use nuxiva_swarm_core::Settings as SwarmSettings;
use tokio::sync::{mpsc, watch};

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

fn env_path(name: &str) -> Option<PathBuf> {
    std::env::var_os(name).map(PathBuf::from)
}

fn ear_endpoint() -> BrainResult<EarEndpoint> {
    let port = std::env::var("NUXIVA_EAR_PORT")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(8093);
    EarEndpoint::loopback("127.0.0.1", port)
}

struct Assembled {
    supervisor: Supervisor,
    events: mpsc::Receiver<Event>,
    dispatcher: Arc<Dispatcher>,
    endpoint: EarEndpoint,
}

async fn assemble() -> BrainResult<Assembled> {
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
    let paths = Paths {
        agents: env_path("NUXIVA_AGENTS_DIR").ok_or(BrainError::Input("agents_dir"))?,
        catalog: env_path("NUXIVA_MCP_CATALOG"),
        public_key: env_path("NUXIVA_MCP_PUBLIC_KEY"),
    };
    let swarm_settings = SwarmSettings::default();
    let (catalog, index) = load_agents(&paths.agents, &swarm_settings)?;
    let (hub, _serial) = build_hub(&paths)?;
    let dispatcher = Arc::new(Dispatcher::new(catalog, swarm_settings, index, hub)?);
    let (supervisor, events) = Supervisor::start(pipeline, memory, SupervisorConfig::default());
    Ok(Assembled {
        supervisor,
        events,
        dispatcher,
        endpoint: ear_endpoint()?,
    })
}

#[tokio::main]
async fn main() -> ExitCode {
    let parts = match assemble().await {
        Ok(parts) => parts,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
    };
    let (merged_tx, merged_rx) = mpsc::channel(128);
    let (stop_tx, stop_rx) = watch::channel(false);
    let link = tokio::spawn(run_ear(parts.endpoint, merged_tx.clone(), stop_rx));
    let mut sensory = parts.events;
    let forward = tokio::spawn(async move {
        while let Some(event) = sensory.recv().await {
            if merged_tx.send(event).await.is_err() {
                break;
            }
        }
    });
    let (out_tx, mut out_rx) = mpsc::channel(64);
    let router = tokio::spawn(route(merged_rx, parts.dispatcher, out_tx));
    let drain = tokio::spawn(async move {
        while let Some(outcome) = out_rx.recv().await {
            match outcome {
                Outcome::Failed(error) => eprintln!("{error}"),
                other => println!("{other:?}"),
            }
        }
    });
    if let Err(error) = tokio::signal::ctrl_c().await {
        eprintln!("{error}");
    }
    let _ = stop_tx.send(true);
    let status = parts.supervisor.shutdown().await;
    let _ = link.await;
    let _ = forward.await;
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
