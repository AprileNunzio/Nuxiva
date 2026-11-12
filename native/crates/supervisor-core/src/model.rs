use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum LoopState {
    Starting,
    Running,
    Restarting,
    Done,
    Halted,
}

impl LoopState {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Starting => "starting",
            Self::Running => "running",
            Self::Restarting => "restarting",
            Self::Done => "done",
            Self::Halted => "halted",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Done,
    Failed,
    Cancelled,
}

impl Outcome {
    #[must_use]
    pub fn parse(text: &str) -> Option<Self> {
        match text {
            "done" => Some(Self::Done),
            "failed" => Some(Self::Failed),
            "cancelled" => Some(Self::Cancelled),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    Finish,
    Halt,
    Restart,
}

impl Action {
    #[must_use]
    pub fn code(self) -> &'static str {
        match self {
            Self::Finish => "finish",
            Self::Halt => "halt",
            Self::Restart => "restart",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Policy {
    pub restart_enabled: bool,
    pub backoff_min: f64,
    pub backoff_max: f64,
    pub stable_after: f64,
    pub report_every: u64,
}

impl Policy {
    #[must_use]
    pub fn sanitized(self) -> Self {
        let clamp = |v: f64, lo: f64, hi: f64| if v.is_finite() { v.clamp(lo, hi) } else { lo };
        let backoff_min = clamp(self.backoff_min, 0.0, 3600.0);
        Self {
            restart_enabled: self.restart_enabled,
            backoff_min,
            backoff_max: clamp(self.backoff_max, backoff_min, 86_400.0),
            stable_after: clamp(self.stable_after, 0.0, 86_400.0),
            report_every: self.report_every.max(1),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Decision {
    pub action: Action,
    pub delay: f64,
    pub report: bool,
    pub restarts: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct LoopView {
    pub name: String,
    pub state: &'static str,
    pub restarts: u64,
    pub stalls: u64,
    pub last_error: String,
    pub up_s: u64,
    pub heartbeat_s: Option<u64>,
    pub period_s: Option<f64>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Totals {
    pub loops: usize,
    pub running: usize,
    pub restarts: u64,
    pub stalls: u64,
}
