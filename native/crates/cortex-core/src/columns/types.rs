use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AbstractionTier {
    Procedural,
    Canonical,
    Invariant,
}

impl AbstractionTier {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Procedural => "procedural",
            Self::Canonical => "canonical",
            Self::Invariant => "invariant",
        }
    }

    #[must_use]
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "procedural" => Some(Self::Procedural),
            "canonical" => Some(Self::Canonical),
            "invariant" => Some(Self::Invariant),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CognitiveDomain {
    Algebraic,
    LogicalSat,
    KinematicControl,
    CausalGraph,
}

impl CognitiveDomain {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Algebraic => "algebraic",
            Self::LogicalSat => "logical_sat",
            Self::KinematicControl => "kinematic_control",
            Self::CausalGraph => "causal_graph",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct InvariantShortcut {
    pub id: String,
    pub pattern_signature: String,
    pub domain: CognitiveDomain,
    pub coefficient_ratio: f64,
    pub constant_offset: f64,
    pub synaptic_strength: f32,
    pub activations: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ColumnResolution {
    pub column_id: String,
    pub domain: CognitiveDomain,
    pub selected_tier: AbstractionTier,
    pub roots: Vec<f64>,
    pub steps_executed: u32,
    pub steps_saved: u32,
    pub invariant_applied: Option<String>,
    pub confidence: f32,
    pub trace_keys: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CorticalColumnSpec {
    pub id: String,
    pub domain: CognitiveDomain,
    pub preferred_tier: AbstractionTier,
    pub maturity_score: f32,
    pub total_executions: u64,
    pub shortcuts_consolidated: u64,
}
