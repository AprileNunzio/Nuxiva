use serde::{Deserialize, Serialize};

use crate::error::{LoopError, LoopResult};

pub const MAX_PAYLOAD: usize = 4 * 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Settings {
    pub max_iterations: u32,
    pub repeat_escalate: u32,
    pub inconclusive_max: u32,
    pub log_chars: usize,
    pub max_files: usize,
    pub required_checks: Vec<String>,
    pub protected_prefixes: Vec<String>,
    pub autonomous_repos: Vec<String>,
    pub audit_cap: usize,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            max_iterations: 5,
            repeat_escalate: 2,
            inconclusive_max: 2,
            log_chars: 4_000,
            max_files: 256,
            required_checks: vec!["test".into(), "lint".into(), "security".into()],
            protected_prefixes: vec![
                "critic/".into(),
                "sandbox/".into(),
                ".github/".into(),
                ".githooks/".into(),
            ],
            autonomous_repos: Vec::new(),
            audit_cap: 1_024,
        }
    }
}

fn name_ok(text: &str) -> bool {
    !text.is_empty()
        && text.len() <= 64
        && text.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'.' | b'_' | b'-')
        })
}

impl Settings {
    pub fn validate(&self) -> LoopResult<()> {
        let ok = (1..=64).contains(&self.max_iterations)
            && (1..=self.max_iterations).contains(&self.repeat_escalate)
            && (1..=16).contains(&self.inconclusive_max)
            && (64..=65_536).contains(&self.log_chars)
            && (1..=4_096).contains(&self.max_files)
            && !self.required_checks.is_empty()
            && self.required_checks.len() <= 32
            && self.required_checks.iter().all(|c| name_ok(c))
            && self.protected_prefixes.len() <= 64
            && self
                .protected_prefixes
                .iter()
                .all(|p| crate::paths::prefix_ok(p))
            && self.autonomous_repos.len() <= 256
            && self
                .autonomous_repos
                .iter()
                .all(|r| crate::gate::repo_ok(r))
            && (1..=65_536).contains(&self.audit_cap);
        if ok { Ok(()) } else { Err(LoopError::Settings) }
    }

    pub fn from_json(text: &str) -> LoopResult<Self> {
        if text.len() > MAX_PAYLOAD {
            return Err(LoopError::TooLarge);
        }
        let settings: Self = serde_json::from_str(text).map_err(|_| LoopError::Settings)?;
        settings.validate()?;
        Ok(settings)
    }
}
