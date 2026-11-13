#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SwarmError {
    Parse,
    TooLarge,
    Invalid,
    Version,
    Cycle,
    UnknownTemplate,
    UnknownIntent,
    IntentMismatch,
    Budget,
    Settings,
    Serialize,
    NoPlanner,
    PlannerFailed,
    GraphNotConsulted,
    GraphStale,
    Direct,
}

impl SwarmError {
    const ALL: [Self; 16] = [
        Self::Parse,
        Self::TooLarge,
        Self::Invalid,
        Self::Version,
        Self::Cycle,
        Self::UnknownTemplate,
        Self::UnknownIntent,
        Self::IntentMismatch,
        Self::Budget,
        Self::Settings,
        Self::Serialize,
        Self::NoPlanner,
        Self::PlannerFailed,
        Self::GraphNotConsulted,
        Self::GraphStale,
        Self::Direct,
    ];

    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::Parse => "swarm.parse",
            Self::TooLarge => "swarm.too_large",
            Self::Invalid => "swarm.invalid",
            Self::Version => "swarm.version",
            Self::Cycle => "swarm.plan.cycle",
            Self::UnknownTemplate => "swarm.plan.unknown_template",
            Self::UnknownIntent => "swarm.plan.unknown_intent",
            Self::IntentMismatch => "swarm.plan.intent_mismatch",
            Self::Budget => "swarm.budget",
            Self::Settings => "swarm.settings.invalid",
            Self::Serialize => "swarm.serialize",
            Self::NoPlanner => "swarm.plan.no_planner",
            Self::PlannerFailed => "swarm.plan.planner_failed",
            Self::GraphNotConsulted => "swarm.graph.not_consulted",
            Self::GraphStale => "swarm.graph.stale",
            Self::Direct => "swarm.direct",
        }
    }

    #[must_use]
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|e| e.code() == code)
    }
}

impl std::fmt::Display for SwarmError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.code())
    }
}

impl std::error::Error for SwarmError {}

pub type SwarmResult<T> = Result<T, SwarmError>;
