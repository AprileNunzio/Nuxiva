use std::collections::{HashSet, VecDeque};
use std::sync::{Mutex, PoisonError};

use serde::{Deserialize, Serialize};

use crate::engine::Outcome;
use crate::error::LoopResult;
use crate::settings::Settings;

#[must_use]
pub fn repo_ok(text: &str) -> bool {
    !text.is_empty()
        && text.len() <= 140
        && text.matches('/').count() == 1
        && text
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'/' | b'.' | b'_' | b'-'))
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Permit {
    digest: String,
}

impl Permit {
    #[must_use]
    pub fn digest(&self) -> &str {
        &self.digest
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case", tag = "kind")]
pub enum Target {
    Local,
    Remote { repo: String },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Decision {
    Allowed,
    NeedsConsent,
    Denied,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Audit {
    pub digest: String,
    pub target: Target,
    pub decision: Decision,
}

#[derive(Debug)]
pub struct Gate {
    settings: Settings,
    state: Mutex<GateState>,
}

#[derive(Debug, Default)]
struct GateState {
    issued: HashSet<String>,
    audit: VecDeque<Audit>,
}

impl Gate {
    pub fn new(settings: Settings) -> LoopResult<Self> {
        settings.validate()?;
        Ok(Self {
            settings,
            state: Mutex::new(GateState::default()),
        })
    }

    pub fn issue(&self, outcome: &Outcome) -> Option<Permit> {
        let Outcome::Passed { artifact, .. } = outcome else {
            return None;
        };
        let mut state = self.state.lock().unwrap_or_else(PoisonError::into_inner);
        state.issued.insert(artifact.digest.clone());
        Some(Permit {
            digest: artifact.digest.clone(),
        })
    }

    pub fn revoke(&self, digest: &str) {
        self.state
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .issued
            .remove(digest);
    }

    pub fn authorize(
        &self,
        permit: Option<&Permit>,
        artifact_digest: &str,
        target: &Target,
        consent: bool,
    ) -> Decision {
        let mut state = self.state.lock().unwrap_or_else(PoisonError::into_inner);
        let valid =
            permit.is_some_and(|p| p.digest == artifact_digest && state.issued.contains(&p.digest));
        let decision = match (valid, target) {
            (false, _) => Decision::Denied,
            (true, Target::Local) => Decision::Allowed,
            (true, Target::Remote { repo }) if !repo_ok(repo) => Decision::Denied,
            (true, Target::Remote { repo })
                if self.settings.autonomous_repos.contains(repo) || consent =>
            {
                Decision::Allowed
            }
            (true, Target::Remote { .. }) => Decision::NeedsConsent,
        };
        if state.audit.len() >= self.settings.audit_cap {
            state.audit.pop_front();
        }
        state.audit.push_back(Audit {
            digest: artifact_digest.to_owned(),
            target: target.clone(),
            decision,
        });
        decision
    }

    #[must_use]
    pub fn audit(&self) -> Vec<Audit> {
        self.state
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .audit
            .iter()
            .cloned()
            .collect()
    }
}
