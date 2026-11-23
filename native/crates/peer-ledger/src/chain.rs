use crate::block::{Block, GENESIS};
use crate::error::{LedgerError, LedgerResult};
use std::collections::VecDeque;

pub const MAX_BLOCKS: usize = 64;
pub const SKEW_MS: i64 = 60_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Applied {
    New,
    Known,
}

#[derive(Debug, Clone, Default)]
pub struct Chain {
    blocks: VecDeque<Block>,
}

impl Chain {
    #[must_use]
    pub fn head(&self) -> Option<&Block> {
        self.blocks.back()
    }

    #[must_use]
    pub fn base_index(&self) -> Option<u64> {
        self.blocks.front().map(|b| b.index)
    }

    #[must_use]
    pub fn next_index(&self) -> u64 {
        self.head().map_or(0, |b| b.index.saturating_add(1))
    }

    #[must_use]
    pub fn next_prev(&self) -> String {
        self.head().map_or_else(|| GENESIS.to_owned(), Block::hash)
    }

    pub fn blocks(&self) -> impl Iterator<Item = &Block> {
        self.blocks.iter()
    }

    pub fn after(&self, index: Option<u64>) -> impl Iterator<Item = &Block> {
        self.blocks
            .iter()
            .filter(move |b| index.is_none_or(|i| b.index > i))
    }

    pub fn accept(&mut self, block: Block, now: i64) -> LedgerResult<Applied> {
        if block.ts > now.saturating_add(SKEW_MS) {
            return Err(LedgerError::Clock);
        }
        let Some(head) = self.blocks.back() else {
            self.blocks.push_back(block);
            return Ok(Applied::New);
        };
        if block.index <= head.index {
            return self.settle_old(&block);
        }
        if Some(block.index) != head.index.checked_add(1) {
            return Err(LedgerError::Gap);
        }
        if block.prev != head.hash() {
            return Err(LedgerError::Link);
        }
        if block.ts < head.ts {
            return Err(LedgerError::Clock);
        }
        self.blocks.push_back(block);
        while self.blocks.len() > MAX_BLOCKS {
            self.blocks.pop_front();
        }
        Ok(Applied::New)
    }

    fn settle_old(&self, block: &Block) -> LedgerResult<Applied> {
        match self.blocks.iter().find(|b| b.index == block.index) {
            Some(known) if known.hash() == block.hash() => Ok(Applied::Known),
            Some(_) => Err(LedgerError::Fork),
            None => Ok(Applied::Known),
        }
    }
}
