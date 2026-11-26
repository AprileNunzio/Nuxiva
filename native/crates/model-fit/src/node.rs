use serde::{Deserialize, Serialize};

use crate::error::{FitError, FitResult};

pub const SATELLITE_MAX_PARAMS_M: u32 = 4_000;
const MAX_MEMORY_MB: u64 = 4 * 1024 * 1024;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NodeClass {
    Server,
    Node,
    Satellite,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Device {
    Gpu,
    Cpu,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Node {
    pub class: NodeClass,
    pub ram_free_mb: u64,
    pub vram_free_mb: u64,
    pub reserve_percent: u8,
    pub on_battery: bool,
}

impl Node {
    pub fn validate(&self) -> FitResult<()> {
        if self.reserve_percent > 90
            || self.ram_free_mb > MAX_MEMORY_MB
            || self.vram_free_mb > MAX_MEMORY_MB
        {
            return Err(FitError::Invalid("node"));
        }
        Ok(())
    }

    #[must_use]
    pub fn usable_mb(&self, device: Device) -> u64 {
        let free = match device {
            Device::Gpu => self.vram_free_mb,
            Device::Cpu => self.ram_free_mb,
        };
        let keep = 100_u64.saturating_sub(u64::from(self.reserve_percent));
        free.saturating_mul(keep) / 100
    }

    #[must_use]
    pub fn max_params_m(&self) -> u32 {
        match (self.class, self.on_battery) {
            (NodeClass::Satellite, true) => SATELLITE_MAX_PARAMS_M / 2,
            (NodeClass::Satellite, false) => SATELLITE_MAX_PARAMS_M,
            _ => u32::MAX,
        }
    }
}
