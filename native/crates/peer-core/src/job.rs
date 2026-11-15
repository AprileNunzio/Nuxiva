use crate::error::{PeerError, PeerResult};
use crate::ident::check_id;
use serde::{Deserialize, Serialize};

pub const MAX_ATTEMPTS: u8 = 8;
pub const MIN_LEASE_MS: u32 = 1_000;
pub const MAX_LEASE_MS: u32 = 600_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Render,
    Compute,
    Background,
}

impl Kind {
    #[must_use]
    pub const fn battery_floor(self) -> u8 {
        match self {
            Self::Render => 15,
            Self::Compute => 30,
            Self::Background => 50,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct Needs {
    pub cpu_cores: u16,
    pub ram_mb: u32,
    pub gpu_vram_mb: u32,
    pub display: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct JobSpec {
    pub id: u64,
    pub kind: Kind,
    pub needs: Needs,
    pub priority: u8,
    pub max_attempts: u8,
    pub lease_ms: u32,
    pub deadline_ms: i64,
    pub min_battery_pct: u8,
    pub requester: String,
    pub affinity: Option<String>,
}

impl JobSpec {
    pub fn validate(&self) -> PeerResult<()> {
        check_id(&self.requester)?;
        if let Some(node) = &self.affinity {
            check_id(node)?;
        }
        let sane = self.id != 0
            && (1..=MAX_ATTEMPTS).contains(&self.max_attempts)
            && (MIN_LEASE_MS..=MAX_LEASE_MS).contains(&self.lease_ms)
            && self.min_battery_pct <= 100
            && self.needs.cpu_cores <= crate::capability::MAX_CORES
            && self.needs.ram_mb <= crate::capability::MAX_RAM_MB
            && self.needs.gpu_vram_mb <= crate::capability::MAX_VRAM_MB;
        if sane { Ok(()) } else { Err(PeerError::Field) }
    }
}
