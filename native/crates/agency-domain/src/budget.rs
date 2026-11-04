use serde::{Deserialize, Serialize};

use crate::error::DomainError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Budget {
    tokens: u64,
    seconds: u64,
    parallel: u16,
}

impl Budget {
    pub fn new(tokens: u64, seconds: u64, parallel: u16) -> Result<Self, DomainError> {
        if tokens == 0 {
            return Err(DomainError::InvalidBudget("tokens must be positive"));
        }
        if seconds == 0 {
            return Err(DomainError::InvalidBudget("seconds must be positive"));
        }
        if parallel == 0 {
            return Err(DomainError::InvalidBudget("parallelism must be positive"));
        }
        Ok(Self {
            tokens,
            seconds,
            parallel,
        })
    }

    #[must_use]
    pub fn max_tokens(&self) -> u64 {
        self.tokens
    }

    #[must_use]
    pub fn max_seconds(&self) -> u64 {
        self.seconds
    }

    #[must_use]
    pub fn max_parallel(&self) -> u16 {
        self.parallel
    }

    #[must_use]
    pub fn allows(&self, usage: &Usage) -> bool {
        usage.tokens <= self.tokens && usage.seconds <= self.seconds
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct Usage {
    tokens: u64,
    seconds: u64,
}

impl Usage {
    #[must_use]
    pub fn tokens(&self) -> u64 {
        self.tokens
    }

    #[must_use]
    pub fn seconds(&self) -> u64 {
        self.seconds
    }

    pub fn record(&mut self, tokens: u64, seconds: u64) -> Result<(), DomainError> {
        let next_tokens = self
            .tokens
            .checked_add(tokens)
            .ok_or(DomainError::Overflow)?;
        let next_seconds = self
            .seconds
            .checked_add(seconds)
            .ok_or(DomainError::Overflow)?;
        self.tokens = next_tokens;
        self.seconds = next_seconds;
        Ok(())
    }
}
