use crate::error::{PeerError, PeerResult};
use serde::{Deserialize, Serialize};

pub const MAX_CORES: u16 = 1024;
pub const MAX_RAM_MB: u32 = 8 * 1024 * 1024;
pub const MAX_VRAM_MB: u32 = 1024 * 1024;
pub const MAX_SCORE: u32 = 1_000_000;
pub const MAX_UPLINK_KBPS: u32 = 100_000_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Tier {
    Server,
    Desktop,
    Mobile,
    Micro,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct Roles {
    pub display: bool,
    pub compute: bool,
    pub coordinate: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Capabilities {
    pub tier: Tier,
    pub roles: Roles,
    pub cpu_cores: u16,
    pub cpu_score: u32,
    pub ram_mb: u32,
    pub gpu_vram_mb: u32,
    pub gpu_score: u32,
    pub battery_pct: Option<u8>,
    pub charging: bool,
    pub uplink_kbps: u32,
    pub rtt_ms: u16,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct Load {
    pub cpu_pct: u8,
    pub ram_free_mb: u32,
    pub jobs_running: u16,
    pub battery_pct: Option<u8>,
    pub charging: bool,
}

impl Capabilities {
    pub fn validate(&self) -> PeerResult<()> {
        let sane = self.cpu_cores <= MAX_CORES
            && self.ram_mb <= MAX_RAM_MB
            && self.gpu_vram_mb <= MAX_VRAM_MB
            && self.cpu_score <= MAX_SCORE
            && self.gpu_score <= MAX_SCORE
            && self.uplink_kbps <= MAX_UPLINK_KBPS
            && self.battery_pct.is_none_or(|b| b <= 100);
        if sane { Ok(()) } else { Err(PeerError::Field) }
    }

    #[must_use]
    pub fn on_battery(&self, load: Option<&Load>) -> Option<u8> {
        let (level, charging) = match load {
            Some(l) => (l.battery_pct.or(self.battery_pct), l.charging),
            None => (self.battery_pct, self.charging),
        };
        if charging { None } else { level }
    }
}

impl Load {
    pub fn validate(&self) -> PeerResult<()> {
        let sane = self.cpu_pct <= 100
            && self.ram_free_mb <= MAX_RAM_MB
            && self.battery_pct.is_none_or(|b| b <= 100);
        if sane { Ok(()) } else { Err(PeerError::Field) }
    }
}
