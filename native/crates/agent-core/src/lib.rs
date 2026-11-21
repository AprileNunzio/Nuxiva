pub mod ceo;
pub mod evolution;
pub mod genesis;
pub mod icon;
pub mod layout;
pub mod manifest;
pub mod registry;
pub mod text;
pub mod widget;
pub mod worker;

pub use evolution::{
    AutonomousCapabilityPackage, ForgedWidgetBundle, MASTERY_PROMOTION_THRESHOLD_BPS,
    MIN_AUTO_FORGE_RECURRING_GAPS, MetaCurriculum, StudyMethod, WidgetForgeSpec,
    evolve_full_capability, forge_widget_bundle, synthesize_meta_curriculum,
};
pub use layout::{LayoutReport, ScaffoldFile, ScaffoldSpec, inspect, scaffold};
pub use manifest::{CATEGORIES, Issue, Manifest, Profile, Report, Routing, Severity, validate};
pub use registry::{Entry, Layout, Origin, Registry, Rejected, Root, Snapshot};
pub use worker::WorkerBlock;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod widget_tests;
