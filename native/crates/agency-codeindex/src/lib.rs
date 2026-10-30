mod scan;
mod search;

pub use scan::{FileEntry, Limits, ScanError, scan};
pub use search::{Hit, search};

#[cfg(test)]
mod tests;
