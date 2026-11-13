use std::collections::HashMap;
use std::sync::{Mutex, PoisonError};
use std::time::{Duration, Instant};

use crate::error::{McpError, McpResult};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConsentKey {
    pub operation: String,
    pub tool: String,
    pub args_hash: String,
}

#[derive(Debug)]
pub struct ConsentLedger {
    ttl: Duration,
    max: usize,
    grants: Mutex<HashMap<String, (ConsentKey, Instant)>>,
}

fn token() -> McpResult<String> {
    let mut bytes = [0u8; 16];
    getrandom::fill(&mut bytes).map_err(|_| McpError::Io)?;
    Ok(bytes
        .iter()
        .flat_map(|b| [b >> 4, b & 15])
        .filter_map(|n| char::from_digit(u32::from(n), 16))
        .collect())
}

impl ConsentLedger {
    #[must_use]
    pub fn new(ttl_ms: u64, max: usize) -> Self {
        Self {
            ttl: Duration::from_millis(ttl_ms),
            max,
            grants: Mutex::new(HashMap::new()),
        }
    }

    pub fn issue(&self, key: ConsentKey, now: Instant) -> McpResult<String> {
        let mut guard = self.grants.lock().unwrap_or_else(PoisonError::into_inner);
        let ttl = self.ttl;
        guard.retain(|_, (_, at)| now.saturating_duration_since(*at) <= ttl);
        if guard.len() >= self.max {
            return Err(McpError::Busy);
        }
        let id = token()?;
        guard.insert(id.clone(), (key, now));
        Ok(id)
    }

    pub fn redeem(&self, id: &str, key: &ConsentKey, now: Instant) -> McpResult<()> {
        let mut guard = self.grants.lock().unwrap_or_else(PoisonError::into_inner);
        let Some((stored, at)) = guard.remove(id) else {
            return Err(McpError::ConsentDenied);
        };
        if &stored == key && now.saturating_duration_since(at) <= self.ttl {
            Ok(())
        } else {
            Err(McpError::ConsentDenied)
        }
    }
}
