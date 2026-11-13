#![forbid(unsafe_code)]

mod build;
mod error;
mod extract;
mod graph;
mod model;
mod path;
mod resolve;
mod settings;
mod source;

pub use build::{build, symbol_label};
pub use error::{GraphError, GraphResult};
pub use extract::{extract, language};
pub use graph::{Graph, GraphStats};
pub use model::{EdgeKind, Fact, Facts, Language, Node, NodeKind, SymKind};
pub use path::validate as validate_path;
pub use settings::GraphSettings;
pub use source::{Entry, FileSource, MemorySource};

#[cfg(test)]
#[allow(
    clippy::expect_used,
    clippy::arithmetic_side_effects,
    clippy::format_collect,
    clippy::cast_possible_truncation
)]
mod tests;
