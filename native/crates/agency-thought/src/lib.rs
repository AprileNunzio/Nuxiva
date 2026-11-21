pub mod agi;
pub mod contracts;
pub mod decomposition;
pub mod error;
pub mod socratic;
pub mod specialist;
pub mod tree;

#[cfg(test)]
mod tests;

pub use agi::{
    AlgorithmicStrategy, AutonomousAgiKernel, EvaluatedPolicy, GodelUpgradeVerdict, IntrinsicGoal,
    PolicyCandidate, SURPRISE_GOAL_THRESHOLD_BPS, TransitionBelief, WorldTransition,
    select_minimal_free_energy_policy,
};
pub use contracts::{ContractKind, ContractRegistry, InterfaceContract};
pub use decomposition::{ExpansionResult, SubTaskBlueprint, expand_task_node};
pub use error::ThoughtError;
pub use socratic::{
    DialecticExchange, EpistemicHypothesis, EpistemicPlan, InquiryScope, ProbeChannel,
    ProbeFinding, ResolutionSource, SocraticReport, classify_resolution, compute_voi_bps,
    interrogate_goal, synthesize_epistemic_plan,
};
pub use specialist::{SpecialistProfile, recruit_specialists, synthesize_autonomous_specialist};
pub use tree::{
    ArchitectureCandidate, EvaluationWeights, RankedBranch, ThoughtVerdict, evaluate_candidates,
};
