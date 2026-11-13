use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const MAX_ALERTS: usize = 5000;
pub const MAX_LIST: usize = 4096;
pub const MAX_TEXT: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    PortScan,
    HostSweep,
    SynFlood,
    BruteForce,
    ArpSpoof,
    DnsTunnel,
    IcmpFlood,
    Exfiltration,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Stage {
    Recon,
    Disruption,
    Intrusion,
    Interception,
    Exfiltration,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Origin {
    Internet,
    Lan,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Posture {
    Calm,
    Watch,
    Alert,
    Attack,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum Autonomy {
    Observe,
    #[default]
    Assist,
    Autonomous,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    Off,
    #[default]
    Monitor,
    Protect,
    Lockdown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ActionKind {
    Warn,
    RateLimit,
    Tarpit,
    Honeypot,
    Block,
    Quarantine,
    CountryBlock,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Alert {
    pub kind: Kind,
    pub severity: Severity,
    #[serde(default)]
    pub src: String,
    #[serde(default)]
    pub dst: String,
    #[serde(default)]
    pub count: u64,
    pub at: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(default)]
#[allow(clippy::struct_excessive_bools)]
pub struct Policy {
    pub autonomy: Autonomy,
    pub mode: Mode,
    pub window_s: f64,
    pub min_level: Severity,
    pub block_minutes: u32,
    pub max_minutes: u32,
    pub tarpit: bool,
    pub honeypot: bool,
    pub quarantine: bool,
    pub country_block: bool,
    pub country_threshold: u32,
    pub home_countries: Vec<String>,
    pub max_actions_per_hour: u32,
}

impl Default for Policy {
    fn default() -> Self {
        Self {
            autonomy: Autonomy::Assist,
            mode: Mode::Monitor,
            window_s: 1800.0,
            min_level: Severity::Medium,
            block_minutes: 60,
            max_minutes: 10_080,
            tarpit: true,
            honeypot: false,
            quarantine: false,
            country_block: false,
            country_threshold: 5,
            home_countries: Vec::new(),
            max_actions_per_hour: 30,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Default)]
#[serde(default)]
pub struct Input {
    pub now: f64,
    pub alerts: Vec<Alert>,
    pub policy: Policy,
    pub trusted: Vec<String>,
    pub protected: Vec<String>,
    pub active: Vec<String>,
    pub strikes: BTreeMap<String, u32>,
    pub countries: BTreeMap<String, String>,
    pub recent_actions: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Incident {
    pub id: String,
    pub src: String,
    pub origin: Origin,
    pub country: String,
    pub kinds: Vec<Kind>,
    pub stage: Stage,
    pub stages: Vec<Stage>,
    pub severity: Severity,
    pub level: Severity,
    pub score: u32,
    pub alerts: u32,
    pub events: u64,
    pub targets: Vec<String>,
    pub first_at: f64,
    pub last_at: f64,
    pub trusted: bool,
    pub protected: bool,
    pub strikes: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Action {
    pub kind: ActionKind,
    pub target: String,
    pub minutes: u32,
    pub reason: String,
    pub incident: String,
    pub auto: bool,
    pub reversible: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CountryStat {
    pub country: String,
    pub incidents: u32,
    pub level: Severity,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Assessment {
    pub posture: Posture,
    pub incidents: Vec<Incident>,
    pub actions: Vec<Action>,
    pub countries: Vec<CountryStat>,
    pub internet: u32,
    pub lan: u32,
}
