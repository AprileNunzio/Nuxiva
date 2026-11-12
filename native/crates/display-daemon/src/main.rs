use std::process::ExitCode;
use std::sync::{Arc, Mutex};

use nuxiva_display::config::Config;
use nuxiva_display::engine::{Engine, SystemClock};
use nuxiva_display::error::DisplayError;
use nuxiva_display::server;
use nuxiva_display_scheduler::Policy;

async fn run() -> Result<(), DisplayError> {
    let config = Config::from_env()?;
    let allowed = Arc::new(config.allowed_uids.clone());
    let engine = Arc::new(Mutex::new(Engine::new(Policy::default(), SystemClock)));
    let listener = server::bind(&config.socket)?;
    eprintln!("display: listening on {}", config.socket.display());
    tokio::select! {
        result = server::serve(listener, engine, allowed) => result,
        signal = tokio::signal::ctrl_c() => signal.map_err(DisplayError::from),
    }
}

fn main() -> ExitCode {
    let runtime = match tokio::runtime::Builder::new_multi_thread()
        .worker_threads(2)
        .enable_all()
        .build()
    {
        Ok(runtime) => runtime,
        Err(error) => {
            eprintln!("display: runtime: {error}");
            return ExitCode::FAILURE;
        }
    };
    match runtime.block_on(run()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("display: {error}");
            ExitCode::FAILURE
        }
    }
}
