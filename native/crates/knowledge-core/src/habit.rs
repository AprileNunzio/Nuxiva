use std::collections::BTreeSet;

use nuxiva_context_core::PersonId;

use crate::error::{KnowledgeError, KnowledgeResult};
use crate::model::{Evidence, Kind, Level, NodeId, NodeRef, Origin, SELF_KEY};
use crate::store::Knowledge;
use crate::text::{clean, normalize};
use crate::write::{Link, Spec};

const DAY_MS: u64 = 86_400_000;
const HOUR_MS: u64 = 3_600_000;
const LOOKBACK_DAYS: u64 = 60;

fn local_parts(at_ms: u64, offset_min: i32) -> (u64, u64) {
    let shift = i64::from(offset_min).saturating_mul(60_000);
    let local = i64::try_from(at_ms)
        .unwrap_or(i64::MAX)
        .saturating_add(shift)
        .max(0);
    let local = u64::try_from(local).unwrap_or(0);
    (
        local.checked_div(DAY_MS).unwrap_or(0),
        local
            .checked_rem(DAY_MS)
            .unwrap_or(0)
            .checked_div(HOUR_MS)
            .unwrap_or(0),
    )
}

impl Knowledge {
    pub fn observe(
        &mut self,
        who: &PersonId,
        label: &str,
        now: u64,
    ) -> KnowledgeResult<Option<NodeId>> {
        let s = self.settings.clone();
        let text = clean(label, s.max_label_chars)?;
        let key = normalize(&text);
        if key.is_empty() {
            return Err(KnowledgeError::Invalid);
        }
        let part = self.own_mut(who)?;
        if !part.observations.contains_key(&key)
            && part.observations.len() >= s.max_observation_keys
        {
            return Err(KnowledgeError::Capacity);
        }
        let samples = part.observations.entry(key).or_default();
        samples.push(now);
        while samples.len() > s.max_samples {
            samples.remove(0);
        }
        let cutoff = now.saturating_sub(LOOKBACK_DAYS.saturating_mul(DAY_MS));
        let recent: Vec<(u64, u64)> = samples
            .iter()
            .filter(|t| **t >= cutoff)
            .map(|t| local_parts(*t, s.utc_offset_min))
            .collect();
        let best = (0_u64..24)
            .map(|start| {
                let days: BTreeSet<u64> = recent
                    .iter()
                    .filter(|(_, hour)| {
                        *hour == start
                            || *hour == start.saturating_add(1).checked_rem(24).unwrap_or(0)
                    })
                    .map(|(day, _)| *day)
                    .collect();
                (days.len(), start)
            })
            .max_by(|a, b| a.0.cmp(&b.0).then(b.1.cmp(&a.1)));
        let Some((days, start)) = best else {
            return Ok(None);
        };
        if days < s.habit_min_days {
            return Ok(None);
        }
        let habit_label = clean(&format!("{text} @{start:02}h"), s.max_label_chars)?;
        let confidence = u32::try_from(days)
            .unwrap_or(0)
            .saturating_mul(100)
            .saturating_add(300)
            .min(600);
        let ev = Evidence {
            origin: Origin::Inference,
            reference: "habit".to_owned(),
            confidence,
        };
        let detail = format!("days={days} hour={start:02}");
        let id = self.remember(
            who,
            &Spec {
                kind: Kind::Habit,
                label: &habit_label,
                detail: Some(&detail),
                level: Level::Private,
            },
            &ev,
            now,
        )?;
        self.relate(
            who,
            &Link {
                from: &NodeRef {
                    kind: Kind::Person,
                    label: SELF_KEY.to_owned(),
                },
                relation: "has_habit",
                to: &NodeRef {
                    kind: Kind::Habit,
                    label: habit_label.clone(),
                },
                level: Level::Private,
            },
            &ev,
            now,
        )?;
        Ok(Some(id))
    }
}
