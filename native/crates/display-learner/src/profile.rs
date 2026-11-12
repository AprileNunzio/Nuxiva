use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::model::Model;
use crate::placement::Placement;
use crate::policy::{LearnerPolicy, decay};
use crate::signal::Kind;

#[derive(Debug, Clone, Copy, PartialEq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Metrics {
    pub shown: f32,
    pub quick_close: f32,
    pub interact: f32,
    pub ask_show: f32,
    pub ask_hide: f32,
    pub expired: f32,
    pub at_ms: u64,
}

impl Metrics {
    pub fn count(&mut self, kind: Kind, now_ms: u64, policy: &LearnerPolicy) {
        let f = decay(
            now_ms.saturating_sub(self.at_ms),
            policy.metrics_half_life_ms,
        );
        for v in [
            &mut self.shown,
            &mut self.quick_close,
            &mut self.interact,
            &mut self.ask_show,
            &mut self.ask_hide,
            &mut self.expired,
        ] {
            *v *= f;
        }
        self.at_ms = self.at_ms.max(now_ms);
        let slot = match kind {
            Kind::Shown => &mut self.shown,
            Kind::QuickClose => &mut self.quick_close,
            Kind::Interact | Kind::Dwell => &mut self.interact,
            Kind::AskShow => &mut self.ask_show,
            Kind::AskHide => &mut self.ask_hide,
            Kind::Expired => &mut self.expired,
            Kind::ClosedAfterUse | Kind::Move | Kind::Resize => return,
        };
        *slot += 1.0;
    }

    #[must_use]
    pub fn sane(&self) -> bool {
        [
            self.shown,
            self.quick_close,
            self.interact,
            self.ask_show,
            self.ask_hide,
            self.expired,
        ]
        .iter()
        .all(|v| v.is_finite() && *v >= 0.0)
    }
}

#[derive(Debug, Clone, PartialEq, Default, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Profile {
    pub models: BTreeMap<String, Model>,
    pub places: BTreeMap<String, Placement>,
    pub metrics: Metrics,
}

impl Profile {
    #[must_use]
    pub fn sane(&self, policy: &LearnerPolicy) -> bool {
        self.models.len() <= policy.max_models
            && self.places.len() <= policy.max_places
            && self.models.values().all(Model::sane)
            && self.places.values().all(Placement::sane)
            && self.metrics.sane()
    }

    pub fn evict_models(&mut self, keep: usize) {
        while self.models.len() > keep {
            let Some(oldest) = self
                .models
                .iter()
                .min_by_key(|(_, m)| m.at_ms())
                .map(|(k, _)| k.clone())
            else {
                return;
            };
            self.models.remove(&oldest);
        }
    }
}
