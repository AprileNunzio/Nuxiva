use std::io::Read;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

pub const CAPTURE_TIMEOUT: Duration = Duration::from_secs(20);
pub const MAX_OUTPUT: u64 = 96 * 1024 * 1024;

pub fn run_bounded(command: &mut Command, timeout: Duration, limit: u64) -> Option<Vec<u8>> {
    let mut child: Child = command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;
    let stdout = child.stdout.take()?;
    let reader = thread::spawn(move || {
        let mut out = Vec::new();
        let mut limited = stdout.take(limit.saturating_add(1));
        limited.read_to_end(&mut out).ok().map(|_| out)
    });
    let deadline = Instant::now().checked_add(timeout)?;
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break Some(status),
            Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(40)),
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                break None;
            }
        }
    };
    let out = reader.join().ok().flatten();
    match (status, out) {
        (Some(s), Some(out)) if s.success() && (out.len() as u64) <= limit => Some(out),
        _ => None,
    }
}

pub fn run_capture(command: &mut Command) -> Option<String> {
    run_bounded(command, Duration::from_secs(5), 1024 * 1024)
        .and_then(|b| String::from_utf8(b).ok())
}
