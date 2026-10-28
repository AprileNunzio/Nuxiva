pub mod basal_ganglia;
pub mod cerebellum;
pub mod limbic;
pub mod neuromodulation;
pub mod thalamus;

pub use basal_ganglia::{BasalGangliaDecision, BasalGangliaGating, CandidateAction};
pub use cerebellum::CerebellarForwardModel;
pub use limbic::{HostSystemTelemetry, LimbicInteroceptiveCore, ThreatAssessment, VisceralState};
pub use neuromodulation::{NeuromodulatorState, NeuromodulatoryBus};
pub use thalamus::{ThalamicChannel, ThalamicRelay};
