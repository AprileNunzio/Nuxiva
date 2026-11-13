use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Level {
    Calm,
    Elevated,
    High,
    Critical,
}

impl Level {
    #[must_use]
    pub const fn rank(self) -> u8 {
        match self {
            Self::Calm => 0,
            Self::Elevated => 1,
            Self::High => 2,
            Self::Critical => 3,
        }
    }

    #[must_use]
    pub const fn from_rank(rank: u8) -> Self {
        match rank {
            0 => Self::Calm,
            1 => Self::Elevated,
            2 => Self::High,
            _ => Self::Critical,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Class {
    Protected,
    High,
    Normal,
    Low,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Kind {
    Process,
    Model,
    Widget,
    Cache,
    Surface,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ActionKind {
    Suspend,
    Unload,
    Hibernate,
    Trim,
    Drop,
    Throttle,
}

#[derive(Debug, Clone, Copy, PartialEq, Default, Deserialize)]
pub struct System {
    pub mem_total: u64,
    pub mem_available: u64,
    #[serde(default)]
    pub swap_total: u64,
    #[serde(default)]
    pub swap_used: u64,
    #[serde(default)]
    pub cpu_percent: f64,
    #[serde(default)]
    pub gpu_percent: f64,
    #[serde(default)]
    pub gpu_mem_total: u64,
    #[serde(default)]
    pub gpu_mem_used: u64,
    #[serde(default)]
    pub cores: u32,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Component {
    pub id: String,
    pub kind: Kind,
    pub class: Class,
    #[serde(default)]
    pub rss: u64,
    #[serde(default)]
    pub budget: Option<u64>,
    #[serde(default)]
    pub idle_ms: u64,
    #[serde(default = "visible_default")]
    pub visible: bool,
    #[serde(default)]
    pub reclaimable: bool,
    #[serde(default)]
    pub cpu_percent: f64,
}

const fn visible_default() -> bool {
    true
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Input {
    pub system: System,
    #[serde(default)]
    pub components: Vec<Component>,
    #[serde(default)]
    pub previous: Option<Level>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Action {
    pub id: String,
    pub action: ActionKind,
    pub reason: &'static str,
    pub reclaim: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Budget {
    pub id: String,
    pub budget: u64,
    pub rss: u64,
    pub over: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Plan {
    pub level: Level,
    pub pressure: f64,
    pub mem_percent: f64,
    pub actions: Vec<Action>,
    pub budgets: Vec<Budget>,
    pub reclaim_total: u64,
    pub protected: Vec<String>,
}
