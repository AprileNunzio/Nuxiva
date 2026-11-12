#![forbid(unsafe_code)]

pub mod changelog;
pub mod impact;
pub mod integrity;
pub mod pipeline;
pub mod rev;
pub mod signature;

pub use changelog::{ChangeEntry, parse_oneline};
pub use impact::{ImpactReport, analyze};
pub use integrity::{IntegrityReport, TreeEntry, blob_oid, parse_ls_tree, verify};
pub use pipeline::{Pipeline, PipelineError, StageStatus};
pub use rev::{InvalidRevision, Revision};
pub use signature::{SignatureReport, Verdict, evaluate};
