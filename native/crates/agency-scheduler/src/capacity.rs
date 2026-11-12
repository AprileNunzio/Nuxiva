use serde::Serialize;

use crate::profile::{HostProfile, ModelProfile};
use crate::settings::{Mode, Settings};

const MIN_SLOT_MB: u64 = 512;
const SLOT_DIVISOR: u64 = 8;
const AGENT_RAM_MB: u64 = 384;
const CPU_CORES_PER_LOCAL_AGENT: u16 = 4;
const CLOUD_REQUESTS_PER_AGENT: u32 = 6;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Limit {
    Manual,
    Cap,
    Memory,
    GpuMemory,
    Cpu,
    RateLimit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Capacity {
    pub parallel_agents: u16,
    pub limit: Limit,
}

fn to_u16(value: u64) -> u16 {
    u16::try_from(value).unwrap_or(u16::MAX)
}

fn local_bounds(host: &HostProfile, size_mb: u64, reserve: u64) -> Vec<(u16, Limit)> {
    let slot = size_mb
        .checked_div(SLOT_DIVISOR)
        .unwrap_or(0)
        .max(MIN_SLOT_MB);
    let on_gpu = host.vram_mb >= size_mb && size_mb > 0;
    let mut bounds = Vec::with_capacity(3);
    if on_gpu {
        let free_vram = host.vram_mb.saturating_sub(size_mb);
        bounds.push((
            to_u16(free_vram.checked_div(slot).unwrap_or(0)),
            Limit::GpuMemory,
        ));
        let free_ram = host.ram_mb.saturating_sub(reserve);
        bounds.push((
            to_u16(free_ram.checked_div(AGENT_RAM_MB).unwrap_or(0)),
            Limit::Memory,
        ));
    } else {
        let free_ram = host.ram_mb.saturating_sub(reserve).saturating_sub(size_mb);
        bounds.push((
            to_u16(
                free_ram
                    .checked_div(slot.saturating_add(AGENT_RAM_MB))
                    .unwrap_or(0),
            ),
            Limit::Memory,
        ));
        bounds.push((
            host.cpu_cores
                .checked_div(CPU_CORES_PER_LOCAL_AGENT)
                .unwrap_or(0),
            Limit::Cpu,
        ));
    }
    bounds
}

fn cloud_bounds(host: &HostProfile, rpm: u32, reserve: u64) -> Vec<(u16, Limit)> {
    let free_ram = host.ram_mb.saturating_sub(reserve);
    vec![
        (
            to_u16(free_ram.checked_div(AGENT_RAM_MB).unwrap_or(0)),
            Limit::Memory,
        ),
        (host.cpu_cores, Limit::Cpu),
        (
            to_u16(u64::from(
                rpm.checked_div(CLOUD_REQUESTS_PER_AGENT).unwrap_or(0),
            )),
            Limit::RateLimit,
        ),
    ]
}

#[must_use]
pub fn capacity(host: &HostProfile, model: &ModelProfile, settings: &Settings) -> Capacity {
    let cap = settings.max_parallel.max(1);
    if settings.mode == Mode::Manual {
        return Capacity {
            parallel_agents: settings.manual_parallel.clamp(1, cap),
            limit: Limit::Manual,
        };
    }
    let bounds = match *model {
        ModelProfile::Local { size_mb } => local_bounds(host, size_mb, settings.reserve_ram_mb),
        ModelProfile::Cloud {
            requests_per_minute,
        } => cloud_bounds(host, requests_per_minute, settings.reserve_ram_mb),
    };
    let (value, limit) = bounds
        .into_iter()
        .chain(std::iter::once((cap, Limit::Cap)))
        .min_by_key(|(value, _)| *value)
        .unwrap_or((1, Limit::Cap));
    Capacity {
        parallel_agents: value.max(1),
        limit,
    }
}
