#![forbid(unsafe_code)]

mod access;
mod consolidate;
mod correct;
mod embed;
mod error;
mod extract;
mod habit;
mod ingest;
mod model;
mod num;
mod read;
mod seal;
mod service;
mod settings;
mod store;
mod text;
mod transfer;
mod vault;
mod wire;
mod write;

pub use consolidate::Report;
pub use correct::Correction;
pub use embed::{DIM, Vector, embed};
pub use error::{KnowledgeError, KnowledgeResult};
pub use extract::{Extractor, Fact};
pub use ingest::IngestReport;
pub use model::{
    Detail, Edge, EdgeId, Evidence, Kind, Level, Node, NodeId, NodeRef, Origin, Provenance,
    SELF_KEY, Status,
};
pub use num::{halve, noisy_or};
pub use read::{Direction, Hit, NeighborQuery, Query, Related, Step};
pub use seal::{MasterKey, OwnerKey};
pub use service::{Clock, Service, system_clock};
pub use settings::KnowledgeSettings;
pub use store::{Knowledge, Partition};
pub use text::{normalize, tokens};
pub use transfer::{ExportBundle, Receipt, confirmation};
pub use vault::Vault;
pub use wire::{Command, MAX_REQUEST};
pub use write::{Change, Link, Outcome, Spec};

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_bench;
#[cfg(test)]
mod tests_concurrency;
#[cfg(test)]
mod tests_life;
#[cfg(test)]
mod tests_privacy;
#[cfg(test)]
mod tests_read;
#[cfg(test)]
mod tests_service;
#[cfg(test)]
mod tests_write;
