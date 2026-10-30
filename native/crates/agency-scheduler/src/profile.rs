use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct HostProfile {
    pub cpu_cores: u16,
    pub ram_mb: u64,
    pub vram_mb: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ModelProfile {
    Local { size_mb: u64 },
    Cloud { requests_per_minute: u32 },
}
