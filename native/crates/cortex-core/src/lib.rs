#![forbid(unsafe_code)]
#![allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_possible_wrap,
    clippy::cast_sign_loss
)]

pub mod columns;
pub mod developmental;
pub mod embodied;
pub mod hippocampus;
pub mod neurons;
pub mod perception;
pub mod platform;
pub mod self_model;
pub mod slots;
pub mod social_tom;
pub mod subcortical;
pub mod workspace;

pub use columns::causal::{CausalGraph, ConditionalProbabilityTable};
pub use columns::cdcl::{CdclSolver, Clause, Literal, SatResult};
pub use columns::confrontation::{
    EpistemicConfrontationRecord, EpistemicDoubtEngine, EpistemicHypothesis,
};
pub use columns::egraph::{EClass, EClassId, EGraph, ENode, RewriteRule};
pub use columns::engine::CorticalCortex;
pub use columns::invariant::{AntiUnificationEngine, SynthesizedMacroRule, TermPattern};
pub use columns::ontology::{
    AxiomaticFormalism, FormalismParadigm, OntologicalAxiom, OntologicalCreativeEngine,
};
pub use columns::types::{
    AbstractionTier, CognitiveDomain, ColumnResolution, CorticalColumnSpec, InvariantShortcut,
};
pub use developmental::bootstrapping::{CoreKnowledgePriors, OntogeneticBootstrapEngine};
pub use developmental::curiosity::IntrinsicCuriosityEngine;
pub use developmental::grounding::{GroundedSymbol, SymbolGroundingEngine};
pub use embodied::active_inference_n_dim::{ActiveInferencePolicy, UniversalActiveInferenceEngine};
pub use embodied::bus::{CanOpenPdoFrame, Cia402State, EtherCatLrwFrame, FieldbusController};
pub use embodied::controller::EmbodiedCortex;
pub use embodied::kinematics32::{HumanoidKinematics34, JOINT_IDS_34};
pub use embodied::types::{ActiveInferenceStep, HumanoidJoint, ImuBalanceState, MotorCommand};
pub use hippocampus::index::NeuronIndex;
pub use hippocampus::tri_synaptic::{
    DentateGyrusPatternSeparator, EpisodicMemoryNode, ModernHopfieldCA3, TriSynapticHippocampus,
};
pub use hippocampus::types::{Decision, SlowReason, Thresholds, Verdict};
pub use neurons::r_stdp::{RStdpConfig, RewardModulatedStdpSynapse};
pub use neurons::sdr::{
    SDR_BIT_SIZE, SDR_DEFAULT_K, SDR_WORD_COUNT, SparseDistributedRepresentation,
};
pub use neurons::spiking::{AdaptiveSpikingNeuron, CompartmentInput, IzhikevichParams};
pub use perception::binding::{BoundPercept, CoordinateTransform, MultimodalSpatiotemporalBinding};
pub use perception::hierarchy::{
    ObjectSlot, PerceptualHierarchyPipeline, RawSensoryFrame, TrackedTrajectory, UnifiedWorldGraph,
    WorldEntityNode,
};
pub use platform::error::{CortexError, CortexResult};
pub use self_model::jtms::{BeliefNode, Justification, JustificationTruthMaintenanceSystem};
pub use self_model::metacognition::SecondOrderMetacognition;
pub use self_model::state::{PersistentSelfModel, UncertaintyState};
pub use slots::types::{SlotDefinition, SlotType, SlotValue};
pub use social_tom::agent_model::AgentMentalModel;
pub use social_tom::bayesian_tom::{
    BayesianTheoryOfMindEngine, SallyAnnePrediction, SallyAnneQuery,
};
pub use social_tom::deception_norms::{PragmaticAssessment, SocialCommunication, SocialNormEngine};
pub use subcortical::basal_ganglia::{BasalGangliaDecision, BasalGangliaGating, CandidateAction};
pub use subcortical::cerebellum::CerebellarForwardModel;
pub use subcortical::limbic::{
    HostSystemTelemetry, LimbicInteroceptiveCore, ThreatAssessment, VisceralState,
};
pub use subcortical::neuromodulation::{NeuromodulatorState, NeuromodulatoryBus};
pub use subcortical::thalamus::{ThalamicChannel, ThalamicRelay};
pub use workspace::ignition::{GlobalWorkspace, IgnitedBroadcast, WorkspaceHypothesis};
