mod archive;
mod text;

pub use archive::{Archive, ArchiveError, Entry, Hit, MAX_LIMIT, NewEntry};
pub use text::{shard, tokens};

#[cfg(test)]
mod tests;
