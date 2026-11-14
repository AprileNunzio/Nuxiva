use std::sync::atomic::{AtomicU8, Ordering};

pub trait ResourceBudget: Send + Sync + std::fmt::Debug {
    fn workers(&self) -> usize;
}

#[derive(Debug, Clone, Copy)]
pub struct FixedBudget(pub usize);

impl ResourceBudget for FixedBudget {
    fn workers(&self) -> usize {
        self.0.max(1)
    }
}

#[derive(Debug)]
pub struct PressureBudget {
    base: usize,
    rank: AtomicU8,
}

impl PressureBudget {
    pub const MAX_RANK: u8 = 3;

    #[must_use]
    pub fn new(base: usize) -> Self {
        Self {
            base: base.max(1),
            rank: AtomicU8::new(0),
        }
    }

    pub fn set_rank(&self, rank: u8) {
        self.rank.store(rank.min(Self::MAX_RANK), Ordering::Relaxed);
    }

    #[must_use]
    pub fn rank(&self) -> u8 {
        self.rank.load(Ordering::Relaxed)
    }
}

impl ResourceBudget for PressureBudget {
    fn workers(&self) -> usize {
        (self.base >> u32::from(self.rank())).max(1)
    }
}
