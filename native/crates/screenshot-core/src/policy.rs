use std::fs;
use std::path::Path;

use crate::config::Config;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Deny {
    Disabled,
    NoTarget,
    Locked,
    Guests,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct State {
    pub locked: bool,
    pub guests: bool,
}

#[must_use]
pub fn guests_present(flag: &Path) -> bool {
    fs::read_to_string(flag).is_ok_and(|v| matches!(v.trim(), "1" | "true" | "yes"))
}

pub fn decide(config: &Config, state: State) -> Result<(), Deny> {
    if !config.enabled {
        return Err(Deny::Disabled);
    }
    if !config.active() {
        return Err(Deny::NoTarget);
    }
    if config.block_locked && state.locked {
        return Err(Deny::Locked);
    }
    if config.block_guests && state.guests {
        return Err(Deny::Guests);
    }
    Ok(())
}
