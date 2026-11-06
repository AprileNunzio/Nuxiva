use nuxiva_sentinel_core::Day;
use serde::{Deserialize, Serialize};

use crate::error::MemoryError;
use crate::index::{IndexKey, Token};
use crate::look::{Color, Headwear, Item, VehicleKind};
use crate::sighting::{Class, Sighting, Who, token};
use crate::store::{open, scan};

pub const MAX_LIMIT: usize = 200;
pub const MAX_SPAN_MS: u64 = 31 * 86_400_000;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Search {
    pub from_ms: u64,
    pub to_ms: u64,
    #[serde(default)]
    pub classes: Vec<Class>,
    #[serde(default)]
    pub who: Option<Who>,
    #[serde(default)]
    pub camera: Option<String>,
    #[serde(default)]
    pub zone: Option<String>,
    #[serde(default)]
    pub upper: Option<Color>,
    #[serde(default)]
    pub lower: Option<Color>,
    #[serde(default)]
    pub headwear: Option<Headwear>,
    #[serde(default)]
    pub face_covered: Option<bool>,
    #[serde(default)]
    pub hi_vis: Option<bool>,
    #[serde(default)]
    pub items: Vec<Item>,
    #[serde(default)]
    pub vehicle: Option<VehicleKind>,
    #[serde(default)]
    pub vehicle_color: Option<Color>,
    #[serde(default = "default_limit")]
    pub limit: usize,
    #[serde(default)]
    pub before: Option<(u64, String)>,
}

const fn default_limit() -> usize {
    50
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Page {
    pub sightings: Vec<Sighting>,
    pub next: Option<(u64, String)>,
    pub scanned: usize,
    pub opened: usize,
}

fn name<T: Serialize>(value: &T) -> String {
    serde_json::to_value(value)
        .ok()
        .and_then(|v| v.as_str().map(str::to_owned))
        .unwrap_or_default()
}

impl Search {
    pub fn validate(&self) -> Result<(), MemoryError> {
        if self.to_ms < self.from_ms || self.to_ms.saturating_sub(self.from_ms) > MAX_SPAN_MS {
            return Err(MemoryError::InvalidSearch("range"));
        }
        if self.limit == 0 || self.limit > MAX_LIMIT {
            return Err(MemoryError::InvalidSearch("limit"));
        }
        if self.classes.len() > 4 || self.items.len() > 6 {
            return Err(MemoryError::InvalidSearch("filter"));
        }
        if self.who.as_ref().is_some_and(|w| !w.valid())
            || self.camera.as_deref().is_some_and(|c| !token(c, 64))
            || self.zone.as_deref().is_some_and(|z| !token(z, 64))
        {
            return Err(MemoryError::InvalidSearch("filter"));
        }
        Ok(())
    }

    fn required(&self, index: &IndexKey) -> Vec<Token> {
        let mut out = Vec::new();
        if let Some(w) = &self.who {
            out.push(index.who(w));
        }
        if let Some(c) = &self.camera {
            out.push(index.token("camera", c));
        }
        if let Some(z) = &self.zone {
            out.push(index.token("zone", z));
        }
        if let Some(c) = self.upper {
            out.push(index.token("upper", &name(&c)));
        }
        if let Some(c) = self.lower {
            out.push(index.token("lower", &name(&c)));
        }
        if let Some(h) = self.headwear {
            out.push(index.token("headwear", &name(&h)));
        }
        if self.face_covered == Some(true) {
            out.push(index.token("face_covered", "1"));
        }
        if self.hi_vis == Some(true) {
            out.push(index.token("hi_vis", "1"));
        }
        for item in &self.items {
            out.push(index.token("item", &name(item)));
        }
        if let Some(v) = self.vehicle {
            out.push(index.token("vehicle", &name(&v)));
        }
        if let Some(c) = self.vehicle_color {
            out.push(index.token("vehicle_color", &name(&c)));
        }
        out
    }

    fn matches(&self, s: &Sighting) -> bool {
        s.end_ms >= self.from_ms
            && s.start_ms <= self.to_ms
            && (self.classes.is_empty() || self.classes.contains(&s.class))
            && self.who.as_ref().is_none_or(|w| *w == s.who)
            && self.camera.as_ref().is_none_or(|c| *c == s.camera)
            && self
                .zone
                .as_ref()
                .is_none_or(|z| s.zone.as_ref() == Some(z))
            && self.upper.is_none_or(|c| s.look.upper == Some(c))
            && self.lower.is_none_or(|c| s.look.lower == Some(c))
            && self.headwear.is_none_or(|h| s.look.headwear == Some(h))
            && self
                .face_covered
                .is_none_or(|f| s.look.face_covered.unwrap_or(false) == f)
            && self
                .hi_vis
                .is_none_or(|f| s.look.hi_vis.unwrap_or(false) == f)
            && self.items.iter().all(|i| s.look.carrying.contains(i))
            && self
                .vehicle
                .is_none_or(|k| s.vehicle.is_some_and(|v| v.kind == k))
            && self
                .vehicle_color
                .is_none_or(|c| s.vehicle.is_some_and(|v| v.color == Some(c)))
            && self
                .before
                .as_ref()
                .is_none_or(|(at, id)| (s.start_ms, &s.id) < (*at, id))
    }

    pub fn day(
        &self,
        day_key: &[u8],
        day: &Day,
        index: &IndexKey,
        data: &[u8],
    ) -> Result<(Vec<Sighting>, usize, usize), MemoryError> {
        let required = self.required(index);
        let classes: Vec<Token> = self.classes.iter().map(|c| index.class(*c)).collect();
        let scanned = scan(day, data)?;
        let mut hits = Vec::new();
        let mut opened = 0_usize;
        for frame in &scanned.frames {
            let tokens = &frame.header.tokens;
            if !required.iter().all(|t| tokens.contains(t))
                || !(classes.is_empty() || classes.iter().any(|t| tokens.contains(t)))
            {
                continue;
            }
            opened = opened.saturating_add(1);
            let s = open(day_key, day, frame)?;
            if self.matches(&s) {
                hits.push(s);
            }
        }
        Ok((hits, scanned.frames.len(), opened))
    }

    pub fn page(
        &self,
        hits: Vec<Sighting>,
        scanned: usize,
        opened: usize,
    ) -> Result<Page, MemoryError> {
        self.validate()?;
        let mut hits = hits;
        hits.sort_by(|a, b| (b.start_ms, &b.id).cmp(&(a.start_ms, &a.id)));
        let more = hits.len() > self.limit;
        hits.truncate(self.limit);
        let next = if more {
            hits.last().map(|s| (s.start_ms, s.id.clone()))
        } else {
            None
        };
        Ok(Page {
            sightings: hits,
            next,
            scanned,
            opened,
        })
    }
}
