use crate::error::{UnderstandError, UnderstandResult};
use crate::goal::{Goal, parse};
use crate::prompt::{Request, build};

pub const DEFAULT_THRESHOLD_BPS: u16 = 8_500;
pub const MAX_USER_BYTES: usize = 4_096;

pub trait Model {
    fn name(&self) -> &str;
    fn complete(&self, request: &Request) -> Result<String, String>;
}

pub struct Understander {
    cascade: Vec<Box<dyn Model>>,
    threshold_bps: u16,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Understood {
    pub goal: Goal,
    pub model: String,
    pub attempts: usize,
}

impl std::fmt::Debug for Understander {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Understander")
            .field("models", &self.cascade.len())
            .field("threshold_bps", &self.threshold_bps)
            .finish()
    }
}

impl Understander {
    #[must_use]
    pub fn new(cascade: Vec<Box<dyn Model>>, threshold_bps: u16) -> Self {
        Self {
            cascade,
            threshold_bps,
        }
    }

    pub fn understand(&self, user: &str, external: Option<&str>) -> UnderstandResult<Understood> {
        if user.trim().is_empty() || user.len() > MAX_USER_BYTES {
            return Err(UnderstandError::Invalid("request"));
        }
        let request = build(user, external);
        let mut best: Option<Understood> = None;
        for (index, model) in self.cascade.iter().enumerate() {
            let attempts = index.saturating_add(1);
            let Ok(raw) = model.complete(&request) else {
                continue;
            };
            let Ok(goal) = parse(&raw, user) else {
                continue;
            };
            let confident = goal.confidence_bps >= self.threshold_bps;
            let candidate = Understood {
                goal,
                model: model.name().to_owned(),
                attempts,
            };
            if confident {
                return Ok(candidate);
            }
            if best
                .as_ref()
                .is_none_or(|b| candidate.goal.confidence_bps > b.goal.confidence_bps)
            {
                best = Some(candidate);
            }
        }
        best.ok_or(UnderstandError::Exhausted)
    }
}
