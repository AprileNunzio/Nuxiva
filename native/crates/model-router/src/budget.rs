use crate::error::{RouteError, RouteResult};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Budget {
    limit_micro: u64,
    spent_micro: u64,
}

impl Budget {
    #[must_use]
    pub fn new(limit_micro: u64) -> Self {
        Self {
            limit_micro,
            spent_micro: 0,
        }
    }

    #[must_use]
    pub fn remaining(&self) -> u64 {
        self.limit_micro.saturating_sub(self.spent_micro)
    }

    #[must_use]
    pub fn spent(&self) -> u64 {
        self.spent_micro
    }

    pub fn reserve(&mut self, micro: u64) -> RouteResult<()> {
        if micro > self.remaining() {
            return Err(RouteError::OverBudget);
        }
        self.spent_micro = self.spent_micro.saturating_add(micro);
        Ok(())
    }

    pub fn refund(&mut self, micro: u64) {
        self.spent_micro = self.spent_micro.saturating_sub(micro);
    }
}
