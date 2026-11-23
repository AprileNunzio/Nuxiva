use crate::block::Block;
use crate::ledger::{Head, Ledger};
use std::collections::BTreeMap;

pub const MAX_SYNC: usize = 64;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct MergeReport {
    pub applied: usize,
    pub known: usize,
    pub rejected: usize,
}

impl Ledger {
    #[must_use]
    pub fn digest(&self) -> Vec<Head> {
        self.chains
            .iter()
            .filter_map(|(author, chain)| {
                chain.head().map(|head| Head {
                    author: author.clone(),
                    index: head.index,
                    hash: head.hash(),
                })
            })
            .collect()
    }

    #[must_use]
    pub fn missing_for(&self, remote: &[Head]) -> Vec<Block> {
        let known: BTreeMap<&str, u64> = remote
            .iter()
            .map(|head| (head.author.as_str(), head.index))
            .collect();
        self.chains
            .iter()
            .flat_map(|(author, chain)| {
                chain
                    .after(known.get(author.as_str()).copied())
                    .cloned()
                    .collect::<Vec<_>>()
            })
            .take(MAX_SYNC)
            .collect()
    }

    pub fn merge(&mut self, mut blocks: Vec<Block>, now: i64) -> MergeReport {
        blocks.truncate(MAX_SYNC);
        blocks.sort_by(|a, b| (&a.author, a.index).cmp(&(&b.author, b.index)));
        let mut report = MergeReport::default();
        for block in blocks {
            match self.accept(block, now) {
                Ok(true) => report.applied = report.applied.saturating_add(1),
                Ok(false) => report.known = report.known.saturating_add(1),
                Err(_) => report.rejected = report.rejected.saturating_add(1),
            }
        }
        report
    }
}
