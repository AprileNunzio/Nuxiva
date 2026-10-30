use std::fs;
use std::path::Path;
use std::process::{Command, Stdio};
use std::thread;

use agency_scheduler::HostProfile;

const NVIDIA_SMI: &str = "/usr/bin/nvidia-smi";

fn ram_mb() -> u64 {
    fs::read_to_string("/proc/meminfo")
        .ok()
        .and_then(|text| {
            text.lines()
                .find(|line| line.starts_with("MemTotal:"))
                .and_then(|line| line.split_whitespace().nth(1))
                .and_then(|kb| kb.parse::<u64>().ok())
        })
        .map_or(0, |kb| kb.checked_div(1024).unwrap_or(0))
}

fn vram_mb() -> u64 {
    if !Path::new(NVIDIA_SMI).is_file() {
        return 0;
    }
    Command::new(NVIDIA_SMI)
        .args(["--query-gpu=memory.total", "--format=csv,noheader,nounits"])
        .stdin(Stdio::null())
        .stderr(Stdio::null())
        .env_clear()
        .output()
        .ok()
        .filter(|out| out.status.success())
        .and_then(|out| String::from_utf8(out.stdout).ok())
        .map_or(0, |text| {
            text.lines()
                .filter_map(|line| line.trim().parse::<u64>().ok())
                .max()
                .unwrap_or(0)
        })
}

#[must_use]
pub fn host(vram_override: Option<u64>) -> HostProfile {
    let cores = thread::available_parallelism().map_or(1, std::num::NonZeroUsize::get);
    HostProfile {
        cpu_cores: u16::try_from(cores).unwrap_or(u16::MAX),
        ram_mb: ram_mb(),
        vram_mb: vram_override.unwrap_or_else(vram_mb),
    }
}
