pub mod anatomy;
mod anatomy_parts;
mod anatomy_plans;
mod build;
pub mod compose;
pub mod cosmos;
pub mod geom;
pub mod plan;

pub use anatomy::{Anatomy, compose_anatomy, preset};
pub use compose::{Traits, compose, schema};
pub use cosmos::{Cosmos, compose_cosmos, cosmos_preset};
pub use geom::{Label, Part, compile, compile_full, palette};
pub use plan::{FormaError, MAX_PARTS, Node, Plan};

#[cfg(test)]
mod tests;

#[cfg(test)]
mod anatomy_tests;

#[cfg(test)]
mod cosmos_tests;
