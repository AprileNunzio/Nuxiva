use crate::capability::Tier;
use crate::job::{JobSpec, Kind};
use crate::registry::{Entry, Status};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Reserved {
    pub cores: u32,
    pub ram_mb: u64,
    pub vram_mb: u64,
    pub jobs: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Needed {
    pub cores: u32,
    pub ram_mb: u64,
    pub vram_mb: u64,
    pub battery_floor: u8,
}

#[must_use]
pub fn needed(spec: &JobSpec, degraded: bool) -> Needed {
    let cores = u32::from(spec.needs.cpu_cores).max(1);
    let ram = u64::from(spec.needs.ram_mb);
    let vram = u64::from(spec.needs.gpu_vram_mb);
    let floor = spec.kind.battery_floor().max(spec.min_battery_pct);
    if degraded {
        Needed {
            cores: (cores / 2).max(1),
            ram_mb: ram / 2,
            vram_mb: vram / 2,
            battery_floor: floor.min(15),
        }
    } else {
        Needed {
            cores,
            ram_mb: ram,
            vram_mb: vram,
            battery_floor: floor,
        }
    }
}

fn free_cores(entry: &Entry, reserved: &Reserved) -> u32 {
    let idle = u32::from(100u8.saturating_sub(entry.load.cpu_pct));
    let usable = u32::from(entry.caps.cpu_cores).saturating_mul(idle) / 100;
    usable.saturating_sub(reserved.cores)
}

fn free_ram(entry: &Entry, reserved: &Reserved) -> u64 {
    let base = if entry.load_seq == 0 {
        u64::from(entry.caps.ram_mb)
    } else {
        u64::from(entry.load.ram_free_mb).min(u64::from(entry.caps.ram_mb))
    };
    base.saturating_sub(reserved.ram_mb)
}

fn free_vram(entry: &Entry, reserved: &Reserved) -> u64 {
    u64::from(entry.caps.gpu_vram_mb).saturating_sub(reserved.vram_mb)
}

#[must_use]
pub fn eligible(entry: &Entry, spec: &JobSpec, reserved: &Reserved, need: &Needed) -> bool {
    if entry.status != Status::Alive || entry.caps.tier == Tier::Micro {
        return false;
    }
    let roles = entry.caps.roles;
    let role_ok = match spec.kind {
        Kind::Render => roles.display || roles.compute,
        Kind::Compute | Kind::Background => roles.compute,
    };
    if !role_ok || (spec.needs.display && !roles.display) {
        return false;
    }
    if let Some(level) = entry.caps.on_battery(Some(&entry.load)) {
        if level < need.battery_floor {
            return false;
        }
    }
    free_cores(entry, reserved) >= need.cores
        && free_ram(entry, reserved) >= need.ram_mb
        && free_vram(entry, reserved) >= need.vram_mb
}

#[must_use]
pub fn score(id: &str, entry: &Entry, spec: &JobSpec, reserved: &Reserved) -> u64 {
    let cpu = u64::from(entry.caps.cpu_score);
    let gpu = u64::from(entry.caps.gpu_score);
    let idle = u64::from(100u8.saturating_sub(entry.load.cpu_pct));
    let compute = cpu.saturating_mul(idle) / 100;
    let mut value = match spec.kind {
        Kind::Render => gpu.saturating_mul(3).saturating_add(compute),
        Kind::Compute => compute.saturating_mul(2).saturating_add(gpu),
        Kind::Background => compute.saturating_mul(2),
    };
    let net = (u64::from(entry.caps.uplink_kbps) / 1_000)
        .min(1_000)
        .saturating_sub(u64::from(entry.caps.rtt_ms));
    value = value.saturating_add(net);
    if let Some(level) = entry.caps.on_battery(Some(&entry.load)) {
        value = value.saturating_mul(u64::from(level)) / 200;
    }
    let busy = u64::from(entry.load.jobs_running).saturating_add(u64::from(reserved.jobs));
    value = value.checked_div(busy.saturating_add(1)).unwrap_or(value);
    if spec.affinity.as_deref() == Some(id) {
        value = value.saturating_add(value / 2);
    }
    value
}
