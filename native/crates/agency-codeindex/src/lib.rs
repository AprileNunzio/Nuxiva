mod index;
mod scan;
mod search;
pub mod symbols;

pub use index::{CodeIndex, CorpusMetrics, IndexError, SyncStats};
pub use scan::{FileEntry, Limits, ScanError, language, scan};
pub use search::{Hit, search};
pub use symbols::{
    CodeSymbol, FileOutline, SymbolHit, SymbolKind, extract_outline, outline_file, search_symbols,
};

#[cfg(test)]
mod tests;
