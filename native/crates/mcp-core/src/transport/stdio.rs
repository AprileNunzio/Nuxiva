use std::path::PathBuf;
use std::process::Stdio;

use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
use tokio::process::Command;
use tokio::sync::mpsc;

use super::link::{Link, QUEUE};
use crate::error::{McpError, McpResult};

#[derive(Debug, Clone)]
pub struct StdioSpec {
    pub program: PathBuf,
    pub args: Vec<String>,
    pub env: Vec<(String, String)>,
}

pub fn spawn_stdio(spec: &StdioSpec, max_line: usize) -> McpResult<Link> {
    let mut child = Command::new(&spec.program)
        .args(&spec.args)
        .env_clear()
        .envs(spec.env.iter().map(|(k, v)| (k.as_str(), v.as_str())))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .kill_on_drop(true)
        .spawn()
        .map_err(|_| McpError::Io)?;
    let mut stdin = child.stdin.take().ok_or(McpError::Io)?;
    let stdout = child.stdout.take().ok_or(McpError::Io)?;
    let (out_tx, mut out_rx) = mpsc::channel::<Vec<u8>>(QUEUE);
    let (in_tx, in_rx) = mpsc::channel::<Vec<u8>>(QUEUE);
    tokio::spawn(async move {
        while let Some(bytes) = out_rx.recv().await {
            if bytes.contains(&b'\n') {
                break;
            }
            let sent = stdin.write_all(&bytes).await.is_ok()
                && stdin.write_all(b"\n").await.is_ok()
                && stdin.flush().await.is_ok();
            if !sent {
                break;
            }
        }
    });
    tokio::spawn(async move {
        let mut reader = BufReader::new(stdout);
        let cap = u64::try_from(max_line)
            .unwrap_or(u64::MAX)
            .saturating_add(1);
        loop {
            let mut line = Vec::new();
            let read = (&mut reader).take(cap).read_until(b'\n', &mut line).await;
            match read {
                Ok(0) | Err(_) => break,
                Ok(_) => {}
            }
            if line.last() != Some(&b'\n') && line.len() > max_line {
                break;
            }
            while matches!(line.last(), Some(b'\n' | b'\r')) {
                line.pop();
            }
            if !line.is_empty() && in_tx.send(line).await.is_err() {
                break;
            }
        }
    });
    let mut link = Link::new(out_tx, in_rx);
    link.guard = Some(Box::new(child));
    Ok(link)
}
