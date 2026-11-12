use serde::Serialize;

use crate::numbers::round_to;

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct GpuSnapshot {
    pub name: String,
    pub gpu_percent: f64,
    pub vram_used: f64,
    pub vram_total: f64,
    pub vram_percent: f64,
    pub temp: Option<f64>,
    pub clock_mhz: Option<f64>,
    pub available: bool,
}

impl Default for GpuSnapshot {
    fn default() -> Self {
        Self {
            name: String::new(),
            gpu_percent: 0.0,
            vram_used: 0.0,
            vram_total: 0.0,
            vram_percent: 0.0,
            temp: None,
            clock_mhz: None,
            available: false,
        }
    }
}

fn finite(text: &str) -> Option<f64> {
    text.trim().parse::<f64>().ok().filter(|v| v.is_finite())
}

#[must_use]
pub fn parse_nvidia_smi(raw: &str) -> Option<GpuSnapshot> {
    let line = raw.trim().lines().next()?;
    let parts: Vec<&str> = line.split(',').map(str::trim).collect();
    if parts.len() < 6 {
        return None;
    }
    let name: String = parts.first()?.chars().take(120).collect();
    let used = finite(parts.get(2)?)?;
    let total = finite(parts.get(3)?)?.max(1.0);
    Some(GpuSnapshot {
        name,
        gpu_percent: finite(parts.get(1)?)?,
        vram_used: round_to(used, 1),
        vram_total: round_to(total, 1),
        vram_percent: round_to(used / total * 100.0, 1),
        temp: Some(finite(parts.get(4)?)?),
        clock_mhz: Some(finite(parts.get(5)?)?),
        available: true,
    })
}
