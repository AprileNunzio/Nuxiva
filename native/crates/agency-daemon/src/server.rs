use std::fs;
use std::os::unix::fs::{FileTypeExt, PermissionsExt};
use std::path::Path;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::net::{UnixListener, UnixStream};
use tokio::sync::Semaphore;
use tokio::time::timeout;

use crate::engine::Engine;
use crate::error::AgencyError;
use crate::protocol::{Request, Response};

const MAX_LINE: u64 = 1024 * 1024;
const MAX_CONNECTIONS: usize = 32;
const IDLE: Duration = Duration::from_secs(60);

pub fn bind(path: &Path) -> Result<UnixListener, AgencyError> {
    if let Ok(meta) = fs::symlink_metadata(path) {
        if !meta.file_type().is_socket() {
            return Err(AgencyError::Config("socket path is taken by another file"));
        }
        fs::remove_file(path)?;
    }
    if let Some(parent) = path.parent() {
        crate::files::private_dir(parent)?;
    }
    let listener = UnixListener::bind(path)?;
    fs::set_permissions(path, fs::Permissions::from_mode(0o600))?;
    Ok(listener)
}

fn authorised(stream: &UnixStream, allowed: &[u32]) -> bool {
    let own = rustix::process::geteuid().as_raw();
    stream
        .peer_cred()
        .is_ok_and(|cred| cred.uid() == own || allowed.contains(&cred.uid()))
}

pub async fn serve(
    listener: UnixListener,
    engine: Arc<Mutex<Engine>>,
    allowed: Arc<Vec<u32>>,
) -> Result<(), AgencyError> {
    let slots = Arc::new(Semaphore::new(MAX_CONNECTIONS));
    loop {
        let (stream, _) = listener.accept().await?;
        if !authorised(&stream, &allowed) {
            drop(stream);
            continue;
        }
        let Ok(permit) = Arc::clone(&slots).try_acquire_owned() else {
            drop(stream);
            continue;
        };
        let engine = Arc::clone(&engine);
        tokio::spawn(async move {
            if let Err(error) = session(stream, engine).await {
                eprintln!("agency: session closed: {error}");
            }
            drop(permit);
        });
    }
}

async fn session(stream: UnixStream, engine: Arc<Mutex<Engine>>) -> Result<(), AgencyError> {
    let (read, mut write) = stream.into_split();
    let mut reader = BufReader::new(read);
    let mut line = String::new();
    loop {
        line.clear();
        let read = timeout(IDLE, (&mut reader).take(MAX_LINE).read_line(&mut line))
            .await
            .map_err(|_| AgencyError::BadRequest("idle timeout".to_owned()))??;
        if read == 0 {
            return Ok(());
        }
        if !line.ends_with('\n') {
            let reply = Response::failure("too_large", "request too large".to_owned());
            write_reply(&mut write, &reply).await?;
            return Ok(());
        }
        let reply = answer(line.trim_end(), &engine).await;
        write_reply(&mut write, &reply).await?;
    }
}

async fn write_reply(
    write: &mut tokio::net::unix::OwnedWriteHalf,
    reply: &Response,
) -> Result<(), AgencyError> {
    let mut bytes = serde_json::to_vec(reply)?;
    bytes.push(b'\n');
    write.write_all(&bytes).await?;
    Ok(())
}

async fn answer(raw: &str, engine: &Arc<Mutex<Engine>>) -> Response {
    let request: Request = match serde_json::from_str(raw) {
        Ok(request) => request,
        Err(error) => return Response::failure("bad_request", error.to_string()),
    };
    let engine = Arc::clone(engine);
    let outcome = tokio::task::spawn_blocking(move || {
        let mut guard = engine
            .lock()
            .map_err(|_| AgencyError::BadRequest("engine unavailable".to_owned()))?;
        guard.handle(request)
    })
    .await;
    match outcome {
        Ok(Ok(data)) => Response::success(data),
        Ok(Err(error)) => {
            if error.code() == "internal" || error.code() == "ledger" {
                eprintln!("agency: {error}");
            }
            Response::failure(error.code(), error.public_message())
        }
        Err(_) => Response::failure("internal", "internal error".to_owned()),
    }
}
