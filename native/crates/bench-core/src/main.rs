#![forbid(unsafe_code)]

use std::io::Write;
use std::process::ExitCode;
use std::time::{SystemTime, UNIX_EPOCH};

fn today() -> u32 {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs());
    u32::try_from(secs / 86_400).unwrap_or(u32::MAX)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match bench_core::execute(&args, today()) {
        Ok(outcome) => {
            if !outcome.stdout.is_empty() {
                let mut out = std::io::stdout().lock();
                if writeln!(out, "{}", outcome.stdout).is_err() {
                    return ExitCode::from(4);
                }
            }
            ExitCode::from(u8::try_from(outcome.code).unwrap_or(4))
        }
        Err(error) => {
            let mut err = std::io::stderr().lock();
            let _ = writeln!(err, "{{\"error\":\"{error}\"}}");
            ExitCode::from(4)
        }
    }
}
