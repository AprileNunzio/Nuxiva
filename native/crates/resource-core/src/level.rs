use crate::model::{Level, System};

const ENTER: [f64; 3] = [60.0, 75.0, 90.0];
const MARGIN: f64 = 8.0;

fn ratio(used: u64, total: u64) -> f64 {
    if total == 0 {
        return 0.0;
    }
    #[allow(clippy::cast_precision_loss)]
    let value = (used as f64) / (total as f64) * 100.0;
    value.clamp(0.0, 100.0)
}

fn clean(value: f64) -> f64 {
    if value.is_finite() {
        value.clamp(0.0, 100.0)
    } else {
        0.0
    }
}

#[must_use]
pub fn mem_percent(system: &System) -> f64 {
    let available = system.mem_available.min(system.mem_total);
    round1(ratio(
        system.mem_total.saturating_sub(available),
        system.mem_total,
    ))
}

#[must_use]
pub fn round1(value: f64) -> f64 {
    (value * 10.0).round() / 10.0
}

#[must_use]
pub fn pressure(system: &System) -> f64 {
    let mem = (mem_percent(system) - 50.0).max(0.0) * 2.0;
    let swap = ratio(system.swap_used, system.swap_total) * 1.5;
    let gpu_mem = ratio(system.gpu_mem_used, system.gpu_mem_total);
    let value = clean(system.cpu_percent)
        .max(clean(system.gpu_percent))
        .max(gpu_mem)
        .max(mem)
        .max(swap);
    round1(value.clamp(0.0, 100.0))
}

#[must_use]
pub fn classify(score: f64, previous: Option<Level>) -> Level {
    let mut rank = 0u8;
    for (index, enter) in ENTER.iter().enumerate() {
        if score >= *enter {
            rank = u8::try_from(index.saturating_add(1)).unwrap_or(3);
        }
    }
    if let Some(prev) = previous {
        let prev_rank = prev.rank();
        if rank < prev_rank {
            let hold = ENTER
                .get(usize::from(prev_rank).saturating_sub(1))
                .copied()
                .unwrap_or(0.0);
            if score >= hold - MARGIN {
                rank = prev_rank;
            }
        }
    }
    Level::from_rank(rank)
}

const GIB: u64 = 1024 * 1024 * 1024;

#[must_use]
pub const fn capacity_scale(system: &System) -> (u64, u64) {
    let ram = system.mem_total;
    let cores = system.cores;
    if ram >= 24 * GIB && cores >= 8 {
        (4, 1)
    } else if ram >= 12 * GIB && cores >= 4 {
        (2, 1)
    } else if ram >= 6 * GIB {
        (1, 1)
    } else {
        (1, 2)
    }
}

#[must_use]
pub const fn idle_limit_ms(level: Level, scale: (u64, u64)) -> u64 {
    let base: u64 = match level {
        Level::Calm => 1_800_000,
        Level::Elevated => 600_000,
        Level::High => 180_000,
        Level::Critical => 30_000,
    };
    match (base.saturating_mul(scale.0)).checked_div(scale.1) {
        Some(v) => v,
        None => base,
    }
}

#[must_use]
pub const fn budget_share(level: Level) -> u64 {
    match level {
        Level::Calm => 100,
        Level::Elevated => 80,
        Level::High => 60,
        Level::Critical => 40,
    }
}
