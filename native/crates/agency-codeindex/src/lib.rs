mod index;
mod scan;
mod search;

pub use index::{CodeIndex, CorpusMetrics, IndexError, SyncStats};
pub use scan::{FileEntry, Limits, ScanError, language, scan};
pub use search::{Hit, search};

#[cfg(test)]
mod tests;
