pub mod ceo;
pub mod icon;
pub mod layout;
pub mod manifest;
pub mod registry;
pub mod text;

pub use layout::{LayoutReport, ScaffoldFile, ScaffoldSpec, inspect, scaffold};
pub use manifest::{CATEGORIES, Issue, Manifest, Profile, Report, Routing, Severity, validate};
pub use registry::{Entry, Layout, Origin, Registry, Rejected, Root, Snapshot};

#[cfg(test)]
mod tests;
