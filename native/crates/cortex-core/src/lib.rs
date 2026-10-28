#![forbid(unsafe_code)]

pub mod columns;
pub mod embodied;
pub mod hippocampus;
pub mod platform;
pub mod slots;

pub use columns::confrontation::{
    EpistemicConfrontationRecord, EpistemicDoubtEngine, EpistemicHypothesis,
};
pub use columns::engine::CorticalCortex;
pub use columns::ontology::{
    AxiomaticFormalism, FormalismParadigm, OntologicalAxiom, OntologicalCreativeEngine,
};
pub use columns::types::{
    AbstractionTier, CognitiveDomain, ColumnResolution, CorticalColumnSpec, InvariantShortcut,
};
pub use embodied::bus::{CanOpenPdoFrame, Cia402State, EtherCatLrwFrame, FieldbusController};
pub use embodied::controller::EmbodiedCortex;
pub use embodied::kinematics32::{HumanoidKinematics34, JOINT_IDS_34};
pub use embodied::types::{ActiveInferenceStep, HumanoidJoint, ImuBalanceState, MotorCommand};
pub use hippocampus::index::NeuronIndex;
pub use hippocampus::types::{Decision, SlowReason, Thresholds, Verdict};
pub use platform::error::{CortexError, CortexResult};
pub use slots::types::{SlotDefinition, SlotType, SlotValue};
