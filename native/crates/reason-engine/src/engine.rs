use capability_registry::{Contract, Registry, Role};
use reason_plan::{Agreement, Plan, Validated, compare, parse, validate};
use reason_understand::{Goal, MAX_USER_BYTES, Request};

use crate::cache::{PlanCache, shape_key};
use crate::catalog::retrieve;
use crate::config::Config;
use crate::error::{EngineError, EngineResult};
use crate::ledger::{GateStatus, Ledger, Sample};
use crate::mode::{Mode, Switch};
use crate::prompt::{PlanRequest, build};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Checked {
    pub plan: Plan,
    pub validated: Validated,
    pub hash: String,
    pub cached: bool,
}

impl Checked {
    #[must_use]
    pub fn executable(&self) -> bool {
        self.validated.missing.is_empty() && self.validated.approvals.is_empty()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Prepared {
    Cached(Box<Checked>),
    Ask(PlanRequest),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    Accepted(Box<Checked>),
    Retry { code: String, request: PlanRequest },
    Rejected(String),
}

#[derive(Debug)]
pub struct Engine {
    registry: Registry,
    config: Config,
    cache: PlanCache,
    ledger: Ledger,
    switch: Switch,
}

#[must_use]
pub fn plan_hash(plan: &Plan) -> String {
    let encoded = serde_json::to_string(plan).unwrap_or_default();
    blake3::hash(encoded.as_bytes()).to_hex().to_string()
}

impl Engine {
    #[must_use]
    pub fn new(config: Config) -> Self {
        Self {
            registry: Registry::new(),
            cache: PlanCache::new(
                usize::try_from(config.cache_capacity).unwrap_or(1),
                config.cache_ttl_ms,
            ),
            config,
            ledger: Ledger::default(),
            switch: Switch::default(),
        }
    }

    pub fn load_registry(&mut self, bytes: &[u8]) -> EngineResult<usize> {
        let registry =
            Registry::from_document(bytes).map_err(|e| EngineError::Registry(e.to_string()))?;
        self.registry = registry;
        self.cache.clear();
        Ok(self.registry.len())
    }

    #[must_use]
    pub fn registry(&self) -> &Registry {
        &self.registry
    }

    #[must_use]
    pub fn config(&self) -> &Config {
        &self.config
    }

    pub fn configure(&mut self, config: Config) -> EngineResult<()> {
        config.validate()?;
        self.cache = PlanCache::new(
            usize::try_from(config.cache_capacity).unwrap_or(1),
            config.cache_ttl_ms,
        );
        self.config = config;
        Ok(())
    }

    pub fn understand_request(user: &str, external: Option<&str>) -> EngineResult<Request> {
        if user.trim().is_empty() || user.len() > MAX_USER_BYTES {
            return Err(EngineError::Goal("request".to_owned()));
        }
        Ok(reason_understand::build(user, external))
    }

    pub fn goal(raw: &str, user: &str) -> EngineResult<Goal> {
        reason_understand::parse(raw, user).map_err(|e| EngineError::Goal(e.to_string()))
    }

    fn contracts(&self, goal: &Goal, user_text: &str, role: Role) -> Vec<&Contract> {
        retrieve(
            &self.registry,
            goal,
            user_text,
            role,
            usize::from(self.config.retrieve_limit),
        )
    }

    pub fn prepare(&mut self, goal: &Goal, user_text: &str, role: Role, now: u64) -> Prepared {
        let key = shape_key(goal, self.registry.generation());
        if let Some(plan) = self.cache.get(&key, now) {
            if let Ok(validated) = validate(&plan, &self.registry, role, goal) {
                return Prepared::Cached(Box::new(Checked {
                    hash: plan_hash(&plan),
                    plan,
                    validated,
                    cached: true,
                }));
            }
            self.cache.forget(&key);
        }
        Prepared::Ask(build(goal, &self.contracts(goal, user_text, role), None))
    }

    pub fn check(
        &self,
        goal: &Goal,
        role: Role,
        raw: &str,
        listed: Option<&[String]>,
    ) -> Result<Checked, String> {
        let plan = parse(raw).map_err(|e| e.to_string())?;
        for step in &plan.steps {
            if let (Some(id), Some(listed)) = (&step.capability, listed) {
                if !listed.iter().any(|l| l == id) {
                    return Err(format!("plan.unlisted_capability.{id}"));
                }
            }
        }
        let validated = validate(&plan, &self.registry, role, goal).map_err(|e| e.to_string())?;
        Ok(Checked {
            hash: plan_hash(&plan),
            plan,
            validated,
            cached: false,
        })
    }

    #[must_use]
    pub fn accept(
        &self,
        goal: &Goal,
        user_text: &str,
        role: Role,
        raw: &str,
        listed: &[String],
        attempt: u8,
    ) -> Verdict {
        match self.check(goal, role, raw, Some(listed)) {
            Ok(checked) => Verdict::Accepted(Box::new(checked)),
            Err(code) if attempt < self.config.max_corrections => Verdict::Retry {
                request: build(goal, &self.contracts(goal, user_text, role), Some(&code)),
                code,
            },
            Err(code) => Verdict::Rejected(code),
        }
    }

    pub fn remember(&mut self, goal: &Goal, checked: &Checked, now: u64) {
        if checked.cached || !checked.validated.missing.is_empty() {
            return;
        }
        let key = shape_key(goal, self.registry.generation());
        self.cache.put(key, checked.plan.clone(), now);
    }

    #[must_use]
    pub fn compare(plan: &Plan, legacy: &[&str]) -> Agreement {
        compare(plan, legacy)
    }

    pub fn record(&mut self, sample: &Sample, now: u64) {
        self.ledger.record(sample, now);
    }

    #[must_use]
    pub fn status(&self, now: u64) -> GateStatus {
        self.ledger.status(&self.config.gate, now)
    }

    #[must_use]
    pub fn mode(&self) -> Switch {
        self.switch
    }

    pub fn set_mode(&mut self, target: Mode, force: bool, now: u64) -> EngineResult<Mode> {
        let status = self.status(now);
        self.switch.set(target, &status, force)
    }

    pub fn restore(&mut self, switch: Switch) {
        self.switch = switch;
    }

    pub fn kill(&mut self) {
        self.switch.kill();
    }

    #[must_use]
    pub fn ledger(&self) -> &Ledger {
        &self.ledger
    }

    pub fn load_ledger(&mut self, ledger: Ledger) {
        self.ledger = ledger;
    }

    pub fn reset_ledger(&mut self) {
        self.ledger.reset();
    }

    #[must_use]
    pub fn cache_stats(&self) -> (usize, u64, u64) {
        let (hits, misses) = self.cache.stats();
        (self.cache.len(), hits, misses)
    }
}
