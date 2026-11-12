pub mod contracts;
pub mod decomposition;
pub mod error;
pub mod socratic;
pub mod specialist;
pub mod tree;

#[cfg(test)]
mod tests;

pub use contracts::{ContractKind, ContractRegistry, InterfaceContract};
pub use decomposition::{ExpansionResult, SubTaskBlueprint, expand_task_node};
pub use error::ThoughtError;
pub use socratic::{
    DialecticExchange, InquiryScope, ResolutionSource, SocraticReport, classify_resolution,
    compute_voi_bps, interrogate_goal,
};
pub use specialist::{SpecialistProfile, recruit_specialists};
pub use tree::{
    ArchitectureCandidate, EvaluationWeights, RankedBranch, ThoughtVerdict, evaluate_candidates,
};
