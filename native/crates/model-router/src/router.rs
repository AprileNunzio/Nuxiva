use crate::budget::Budget;
use crate::error::{RouteError, RouteResult};
use crate::profile::{Placement, Profile, Sensitivity, Task};

pub const MIN_QUALITY_BPS: u16 = 6_000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Request {
    pub task: Task,
    pub sensitivity: Sensitivity,
    pub input_tokens: u32,
    pub max_output: u32,
    pub min_quality_bps: u16,
    pub deadline_ms: Option<u32>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Decision {
    pub model: String,
    pub cost_micro: u64,
    pub fallbacks: Vec<String>,
}

#[derive(Debug, Default)]
pub struct Router {
    profiles: Vec<Profile>,
}

impl Router {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    pub fn register(&mut self, profile: Profile) -> RouteResult<()> {
        profile.validate()?;
        self.profiles.retain(|p| p.id != profile.id);
        self.profiles.push(profile);
        Ok(())
    }

    pub fn remove(&mut self, id: &str) {
        self.profiles.retain(|p| p.id != id);
    }

    fn eligible(&self, req: &Request) -> Vec<&Profile> {
        let need = req.input_tokens.saturating_add(req.max_output);
        let floor = req.min_quality_bps.max(MIN_QUALITY_BPS);
        let mut out: Vec<&Profile> = self
            .profiles
            .iter()
            .filter(|p| p.context_tokens >= need)
            .filter(|p| p.quality(req.task) >= floor)
            .filter(|p| req.sensitivity < Sensitivity::Secret || p.placement == Placement::Local)
            .filter(|p| req.deadline_ms.is_none_or(|d| p.latency_ms <= d))
            .collect();
        out.sort_by(|a, b| {
            let ca = a.cost(req.input_tokens, req.max_output);
            let cb = b.cost(req.input_tokens, req.max_output);
            let local = |p: &Profile| u8::from(p.placement == Placement::Cloud);
            local(a)
                .cmp(&local(b))
                .then(ca.cmp(&cb))
                .then(a.quality(req.task).cmp(&b.quality(req.task)))
                .then(a.id.cmp(&b.id))
        });
        out
    }

    pub fn choose(&self, req: &Request, budget: &mut Budget) -> RouteResult<Decision> {
        let candidates = self.eligible(req);
        if candidates.is_empty() {
            return Err(RouteError::NoModel);
        }
        let affordable: Vec<&Profile> = candidates
            .into_iter()
            .filter(|p| p.cost(req.input_tokens, req.max_output) <= budget.remaining())
            .collect();
        let Some(first) = affordable.first() else {
            return Err(RouteError::OverBudget);
        };
        let cost = first.cost(req.input_tokens, req.max_output);
        budget.reserve(cost)?;
        Ok(Decision {
            model: first.id.clone(),
            cost_micro: cost,
            fallbacks: affordable.iter().skip(1).map(|p| p.id.clone()).collect(),
        })
    }
}
