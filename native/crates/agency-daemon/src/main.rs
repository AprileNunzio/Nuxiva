use std::process::ExitCode;
use std::sync::{Arc, Mutex};

use nuxiva_agency::config::Config;
use nuxiva_agency::engine::Engine;
use nuxiva_agency::error::AgencyError;
use nuxiva_agency::{probe, server};

async fn run() -> Result<(), AgencyError> {
    let config = Config::from_env()?;
    let host = probe::host(config.vram_mb);
    let allowed = Arc::new(config.allowed_uids.clone());
    let socket = config.socket.clone();
    let engine = Arc::new(Mutex::new(Engine::open(config, host)?));
    let listener = server::bind(&socket)?;
    eprintln!("agency: listening on {}", socket.display());
    tokio::select! {
        result = server::serve(listener, engine, allowed) => result,
        signal = tokio::signal::ctrl_c() => signal.map_err(AgencyError::from),
    }
}

fn main() -> ExitCode {
    let runtime = match tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(error) => {
            eprintln!("agency: runtime: {error}");
            return ExitCode::FAILURE;
        }
    };
    match runtime.block_on(run()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("agency: {error}");
            ExitCode::FAILURE
        }
    }
}
