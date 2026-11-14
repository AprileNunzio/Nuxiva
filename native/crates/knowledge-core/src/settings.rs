use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::Kind;

const DAY_MS: u64 = 86_400_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct KnowledgeSettings {
    pub max_partitions: usize,
    pub max_nodes: usize,
    pub max_edges: usize,
    pub max_label_chars: usize,
    pub max_detail_chars: usize,
    pub max_provenance: usize,
    pub max_limit: usize,
    pub max_depth: usize,
    pub expansion_decay: u32,
    pub min_score: u32,
    pub reinforce_gain: u32,
    pub half_life_ms: BTreeMap<Kind, u64>,
    pub forget_floor: u32,
    pub forget_min_age_ms: u64,
    pub max_forget_per_pass: usize,
    pub merge_threshold: u32,
    pub max_merge_per_pass: usize,
    pub functional: Vec<String>,
    pub utc_offset_min: i32,
    pub habit_min_days: usize,
    pub max_observation_keys: usize,
    pub max_samples: usize,
}

impl Default for KnowledgeSettings {
    fn default() -> Self {
        let half_life_ms = [
            (Kind::Person, 365_u64),
            (Kind::Place, 180),
            (Kind::Object, 120),
            (Kind::Habit, 90),
            (Kind::Preference, 120),
            (Kind::Event, 30),
            (Kind::Concept, 90),
        ]
        .into_iter()
        .map(|(kind, days)| (kind, days.saturating_mul(DAY_MS)))
        .collect();
        Self {
            max_partitions: 1_000,
            max_nodes: 200_000,
            max_edges: 800_000,
            max_label_chars: 120,
            max_detail_chars: 1_000,
            max_provenance: 8,
            max_limit: 50,
            max_depth: 3,
            expansion_decay: 500,
            min_score: 120,
            reinforce_gain: 150,
            half_life_ms,
            forget_floor: 40,
            forget_min_age_ms: 14_u64.saturating_mul(DAY_MS),
            max_forget_per_pass: 200,
            merge_threshold: 930,
            max_merge_per_pass: 100,
            functional: ["lives_in", "works_as", "works_at", "born_in", "spouse"]
                .iter()
                .map(|s| (*s).to_owned())
                .collect(),
            utc_offset_min: 0,
            habit_min_days: 3,
            max_observation_keys: 512,
            max_samples: 64,
        }
    }
}

fn within(value: usize, ceiling: usize) -> bool {
    (1..=ceiling).contains(&value)
}

impl KnowledgeSettings {
    pub fn validate(&self) -> KnowledgeResult<()> {
        let ok = within(self.max_partitions, 100_000)
            && within(self.max_nodes, 1_000_000)
            && within(self.max_edges, 4_000_000)
            && within(self.max_label_chars, 400)
            && within(self.max_detail_chars, 8_000)
            && within(self.max_provenance, 64)
            && within(self.max_limit, 200)
            && within(self.max_depth, 6)
            && within(self.max_forget_per_pass, 100_000)
            && within(self.max_merge_per_pass, 10_000)
            && within(self.habit_min_days, 365)
            && within(self.max_observation_keys, 100_000)
            && within(self.max_samples, 1_024)
            && (1..=1000).contains(&self.expansion_decay)
            && self.min_score <= 1000
            && (1..=1000).contains(&self.reinforce_gain)
            && self.forget_floor <= 1000
            && (500..=1000).contains(&self.merge_threshold)
            && (-840..=840).contains(&self.utc_offset_min)
            && Kind::ALL
                .iter()
                .all(|k| self.half_life_ms.get(k).is_some_and(|v| *v >= DAY_MS))
            && self.functional.len() <= 64
            && self
                .functional
                .iter()
                .all(|f| crate::text::relation_name(f).is_ok());
        if ok {
            Ok(())
        } else {
            Err(KnowledgeError::Settings)
        }
    }

    pub fn from_json(raw: &str) -> KnowledgeResult<Self> {
        if raw.len() > 64 * 1024 {
            return Err(KnowledgeError::TooLarge);
        }
        let parsed: Self = serde_json::from_str(raw).map_err(|_| KnowledgeError::Settings)?;
        parsed.validate()?;
        Ok(parsed)
    }

    #[must_use]
    pub fn half_life(&self, kind: Kind) -> u64 {
        self.half_life_ms
            .get(&kind)
            .copied()
            .unwrap_or(90_u64.saturating_mul(DAY_MS))
    }

    #[must_use]
    pub fn is_functional(&self, relation: &str) -> bool {
        self.functional.iter().any(|f| f == relation)
    }
}
