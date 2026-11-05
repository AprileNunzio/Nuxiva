#![forbid(unsafe_code)]

pub mod candidate;
pub mod category;
pub mod context;
pub mod grid;
pub mod nucleus;
pub mod plan;
pub mod policy;
pub mod score;
pub mod select;

pub use candidate::{Candidate, Size};
pub use category::{Category, category_of};
pub use context::{Context, Mode, Previous, Screen};
pub use nucleus::Nucleus;
pub use plan::{Explain, Placed, ScenePlan, plan};
pub use policy::PlannerPolicy;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_props;
