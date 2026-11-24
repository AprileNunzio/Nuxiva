use std::collections::{BTreeMap, BTreeSet};

use model_router::Sensitivity;

use crate::model::{Classifier, Input, MAX_TEXT_BYTES, Node, Platform, Reason, Route};

pub const BREAKER_FAILURES: u8 = 3;
pub const BREAKER_COOLDOWN_MS: u64 = 60_000;

#[derive(Debug, Clone, Copy, Default)]
struct Breaker {
    failures: u8,
    opened_at: Option<u64>,
}

#[derive(Debug)]
pub struct Adapter {
    key_present: bool,
    platforms: BTreeSet<Platform>,
    enabled_nodes: BTreeSet<String>,
    breakers: BTreeMap<String, Breaker>,
}

impl Adapter {
    #[must_use]
    pub fn new(
        key_present: bool,
        platforms: impl IntoIterator<Item = Platform>,
        enabled_nodes: impl IntoIterator<Item = String>,
    ) -> Self {
        Self {
            key_present,
            platforms: platforms.into_iter().collect(),
            enabled_nodes: enabled_nodes.into_iter().collect(),
            breakers: BTreeMap::new(),
        }
    }

    fn gate(&self, node: &Node, input: &Input<'_>, now_ms: u64) -> Option<Reason> {
        if !self.key_present {
            return Some(Reason::NoKey);
        }
        if node.id.is_empty() || !self.enabled_nodes.contains(&node.id) {
            return Some(Reason::NodeNotEnabled);
        }
        if !self.platforms.contains(&node.platform) {
            return Some(Reason::UnsupportedPlatform);
        }
        if input.text.len() > MAX_TEXT_BYTES {
            return Some(Reason::TooLong);
        }
        if input.attachments.any() {
            return Some(Reason::RichInput);
        }
        if input.sensitivity != Sensitivity::Public {
            return Some(Reason::NotPublic);
        }
        let open = self
            .breakers
            .get(&node.id)
            .and_then(|b| b.opened_at)
            .is_some_and(|at| now_ms.saturating_sub(at) < BREAKER_COOLDOWN_MS);
        open.then_some(Reason::BreakerOpen)
    }

    pub fn route<C: Classifier>(
        &mut self,
        node: &Node,
        input: &Input<'_>,
        classifier: &mut C,
        now_ms: u64,
    ) -> Route {
        if let Some(reason) = self.gate(node, input, now_ms) {
            return Route::Deep(reason);
        }
        let breaker = self.breakers.entry(node.id.clone()).or_default();
        if let Ok(simple) = classifier.is_simple(input.text) {
            *breaker = Breaker::default();
            if simple {
                Route::Jev
            } else {
                Route::Deep(Reason::NotSimple)
            }
        } else {
            breaker.failures = breaker.failures.saturating_add(1);
            if breaker.failures >= BREAKER_FAILURES {
                breaker.opened_at = Some(now_ms);
            }
            Route::Deep(Reason::Unavailable)
        }
    }
}
