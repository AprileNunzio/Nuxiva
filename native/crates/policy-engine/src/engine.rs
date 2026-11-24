use std::collections::BTreeSet;

use capability_registry::{Contract, Effect, Role, State};

use crate::policy::{Policy, matches};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Why {
    Inactive,
    RoleTooLow,
    EffectAboveCeiling,
    ContextDenied,
    ContextEffects,
    UserDenied,
    UserNotListed,
    UnknownContext,
}

impl Why {
    #[must_use]
    pub fn key(self) -> &'static str {
        match self {
            Self::Inactive => "policy.deny.inactive",
            Self::RoleTooLow => "policy.deny.role_too_low",
            Self::EffectAboveCeiling => "policy.deny.effect_above_ceiling",
            Self::ContextDenied => "policy.deny.context_denied",
            Self::ContextEffects => "policy.deny.context_effects",
            Self::UserDenied => "policy.deny.user_denied",
            Self::UserNotListed => "policy.deny.user_not_listed",
            Self::UnknownContext => "policy.deny.unknown_context",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Decision {
    Allow,
    Approve,
    Deny(Why),
}

#[derive(Debug, Clone, Copy)]
pub struct Subject<'a> {
    pub user: &'a str,
    pub role: Role,
}

#[derive(Debug, Clone)]
pub struct Engine {
    policy: Policy,
    generation: u64,
}

impl Engine {
    #[must_use]
    pub fn new(policy: Policy) -> Self {
        Self {
            policy,
            generation: 1,
        }
    }

    pub fn replace(&mut self, policy: Policy) {
        self.policy = policy;
        self.generation = self.generation.saturating_add(1);
    }

    #[must_use]
    pub fn generation(&self) -> u64 {
        self.generation
    }

    #[must_use]
    pub fn decide(&self, subject: &Subject<'_>, context: &str, contract: &Contract) -> Decision {
        if contract.state != State::Active {
            return Decision::Deny(Why::Inactive);
        }
        if !subject.role.permits(contract.min_role) {
            return Decision::Deny(Why::RoleTooLow);
        }
        if !contract
            .effects
            .is_subset(&self.policy.ceiling(subject.role))
        {
            return Decision::Deny(Why::EffectAboveCeiling);
        }
        let Some(rule) = self.policy.contexts.get(context) else {
            return Decision::Deny(Why::UnknownContext);
        };
        if rule.deny.iter().any(|p| matches(p, &contract.id)) {
            return Decision::Deny(Why::ContextDenied);
        }
        if let Some(max) = &rule.max_effects {
            if !contract.effects.is_subset(max) {
                return Decision::Deny(Why::ContextEffects);
            }
        }
        if let Some(user) = self.policy.users.get(subject.user) {
            if user.deny.iter().any(|p| matches(p, &contract.id)) {
                return Decision::Deny(Why::UserDenied);
            }
            if let Some(only) = &user.allow_only {
                if !only.iter().any(|p| matches(p, &contract.id)) {
                    return Decision::Deny(Why::UserNotListed);
                }
            }
        }
        let flagged = rule.approve.iter().any(|p| matches(p, &contract.id));
        let risky = contract.requires_approval() || contract.effects.contains(&Effect::Spend);
        if flagged || risky {
            Decision::Approve
        } else {
            Decision::Allow
        }
    }

    #[must_use]
    pub fn allowed_ids<'a>(
        &self,
        subject: &Subject<'_>,
        context: &str,
        contracts: impl IntoIterator<Item = &'a Contract>,
    ) -> BTreeSet<&'a str> {
        contracts
            .into_iter()
            .filter(|c| !matches!(self.decide(subject, context, c), Decision::Deny(_)))
            .map(|c| c.id.as_str())
            .collect()
    }
}
