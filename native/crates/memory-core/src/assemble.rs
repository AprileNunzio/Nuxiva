use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::error::MemoryError;
use crate::look::{Build, Color, Headwear, Item, Look, Vehicle, VehicleKind};
use crate::sighting::{Class, Evidence, MAX_EVIDENCE, Sighting, Who, token};

pub const MAX_OPEN: usize = 256;
pub const MIN_IOU: f32 = 0.2;
pub const MAX_SHIFT: f32 = 0.15;
pub const WHO_SHARE: f32 = 0.6;
pub const ITEM_SHARE: f32 = 0.3;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Observation {
    pub camera: String,
    pub at_ms: u64,
    pub class: Class,
    #[serde(rename = "box")]
    pub bbox: [f32; 4],
    #[serde(default)]
    pub track: Option<String>,
    #[serde(default)]
    pub zone: Option<String>,
    #[serde(default)]
    pub who: Option<Who>,
    #[serde(default)]
    pub look: Look,
    #[serde(default)]
    pub vehicle: Option<Vehicle>,
    #[serde(default)]
    pub evidence: Option<Evidence>,
    pub score: f32,
}

impl Observation {
    pub fn validate(&self) -> Result<(), MemoryError> {
        let unit = |v: &f32| v.is_finite() && (0.0..=1.0).contains(v);
        if !token(&self.camera, 64)
            || self.zone.as_deref().is_some_and(|z| !token(z, 64))
            || self.track.as_deref().is_some_and(|t| !token(t, 64))
        {
            return Err(MemoryError::InvalidSighting("place"));
        }
        if !self.bbox.iter().all(unit) || !unit(&self.score) {
            return Err(MemoryError::InvalidSighting("box"));
        }
        if self.who.as_ref().is_some_and(|w| !w.valid()) || !self.look.valid() {
            return Err(MemoryError::InvalidSighting("who"));
        }
        if self.vehicle.is_some() != (self.class == Class::Vehicle) {
            return Err(MemoryError::InvalidSighting("vehicle"));
        }
        Ok(())
    }
}

#[derive(Debug, Clone)]
struct Votes<K: Ord> {
    counts: BTreeMap<K, usize>,
    total: usize,
}

impl<K: Ord> Default for Votes<K> {
    fn default() -> Self {
        Self {
            counts: BTreeMap::new(),
            total: 0,
        }
    }
}

impl<K: Ord + Clone> Votes<K> {
    fn add(&mut self, key: Option<K>) {
        if let Some(k) = key {
            let slot = self.counts.entry(k).or_insert(0);
            *slot = slot.saturating_add(1);
            self.total = self.total.saturating_add(1);
        }
    }

    #[allow(clippy::cast_precision_loss)]
    fn winner(&self, share: f32) -> Option<K> {
        let (key, count) = self
            .counts
            .iter()
            .max_by(|a, b| a.1.cmp(b.1).then(b.0.cmp(a.0)))?;
        (*count as f32 >= share * self.total as f32).then(|| key.clone())
    }
}

#[derive(Debug, Clone)]
struct Open {
    camera: String,
    class: Class,
    track: Option<String>,
    zone: Option<String>,
    start: u64,
    last: u64,
    bbox: [f32; 4],
    seen: usize,
    score: f32,
    who: Votes<String>,
    people: BTreeMap<String, Who>,
    upper: Votes<Color>,
    lower: Votes<Color>,
    headwear: Votes<Headwear>,
    build: Votes<Build>,
    flags: [Votes<bool>; 4],
    items: BTreeMap<Item, usize>,
    heights: Vec<u16>,
    vehicle: Votes<VehicleKind>,
    vehicle_color: Votes<Color>,
    evidence: Vec<Evidence>,
}

fn iou(a: &[f32; 4], b: &[f32; 4]) -> f32 {
    let [ax, ay, aw, ah] = *a;
    let [bx, by, bw, bh] = *b;
    let w = ((ax + aw).min(bx + bw) - ax.max(bx)).max(0.0);
    let h = ((ay + ah).min(by + bh) - ay.max(by)).max(0.0);
    let inter = w * h;
    let union = aw * ah + bw * bh - inter;
    if union <= f32::EPSILON {
        0.0
    } else {
        inter / union
    }
}

fn shift(a: &[f32; 4], b: &[f32; 4]) -> f32 {
    let [ax, ay, aw, ah] = *a;
    let [bx, by, bw, bh] = *b;
    let dx = (ax + aw / 2.0) - (bx + bw / 2.0);
    let dy = (ay + ah / 2.0) - (by + bh / 2.0);
    dx.hypot(dy)
}

impl Open {
    fn new(o: &Observation) -> Self {
        Self {
            camera: o.camera.clone(),
            class: o.class,
            track: o.track.clone(),
            zone: o.zone.clone(),
            start: o.at_ms,
            last: o.at_ms,
            bbox: o.bbox,
            seen: 0,
            score: 0.0,
            who: Votes::default(),
            people: BTreeMap::new(),
            upper: Votes::default(),
            lower: Votes::default(),
            headwear: Votes::default(),
            build: Votes::default(),
            flags: Default::default(),
            items: BTreeMap::new(),
            heights: Vec::new(),
            vehicle: Votes::default(),
            vehicle_color: Votes::default(),
            evidence: Vec::new(),
        }
    }

    fn absorb(&mut self, o: &Observation) {
        self.last = self.last.max(o.at_ms);
        self.start = self.start.min(o.at_ms);
        self.bbox = o.bbox;
        self.seen = self.seen.saturating_add(1);
        self.score += o.score;
        if self.zone.is_none() {
            self.zone.clone_from(&o.zone);
        }
        if let Some(w) = o.who.as_ref().filter(|w| **w != Who::Unknown) {
            self.people.insert(w.key(), w.clone());
            self.who.add(Some(w.key()));
        }
        let l = &o.look;
        self.upper.add(l.upper);
        self.lower.add(l.lower);
        self.headwear.add(l.headwear);
        self.build.add(l.build);
        for (slot, value) in
            self.flags
                .iter_mut()
                .zip([l.face_covered, l.glasses, l.beard, l.hi_vis])
        {
            slot.add(value);
        }
        for item in &l.carrying {
            let n = self.items.entry(*item).or_insert(0);
            *n = n.saturating_add(1);
        }
        if let Some(h) = l.height_cm {
            self.heights.push(h);
        }
        if let Some(v) = o.vehicle {
            self.vehicle.add(Some(v.kind));
            self.vehicle_color.add(v.color);
        }
        if let Some(e) = &o.evidence {
            if self.evidence.len() < MAX_EVIDENCE {
                self.evidence.push(e.clone());
            } else if let Some(slot) = self.evidence.last_mut() {
                *slot = e.clone();
            }
        }
    }

    fn fits(&self, o: &Observation, idle_ms: u64) -> Option<f32> {
        if self.camera != o.camera || self.class != o.class {
            return None;
        }
        if o.at_ms.saturating_sub(self.last) > idle_ms
            || self.last.saturating_sub(o.at_ms) > idle_ms
        {
            return None;
        }
        if let (Some(a), Some(b)) = (&self.track, &o.track) {
            return (a == b).then_some(2.0);
        }
        let overlap = iou(&self.bbox, &o.bbox);
        if overlap >= MIN_IOU {
            return Some(1.0 + overlap);
        }
        let d = shift(&self.bbox, &o.bbox);
        (d <= MAX_SHIFT).then_some(1.0 - d)
    }

    #[allow(clippy::cast_precision_loss)]
    fn finish(mut self) -> Sighting {
        let who = self
            .who
            .winner(WHO_SHARE)
            .filter(|_| self.who.total.saturating_mul(2) >= self.seen.min(4))
            .and_then(|k| self.people.remove(&k))
            .unwrap_or(Who::Unknown);
        let flag = |v: &Votes<bool>| v.winner(0.5);
        let [f0, f1, f2, f3] = &self.flags;
        let [face_covered, glasses, beard, hi_vis] = [flag(f0), flag(f1), flag(f2), flag(f3)];
        let seen = self.seen.max(1);
        let mut carrying: Vec<Item> = self
            .items
            .iter()
            .filter(|(_, n)| **n as f32 >= ITEM_SHARE * seen as f32)
            .map(|(i, _)| *i)
            .collect();
        carrying.truncate(crate::look::MAX_ITEMS);
        self.heights.sort_unstable();
        let vehicle = self.vehicle.winner(0.0).map(|kind| Vehicle {
            kind,
            color: self.vehicle_color.winner(0.5),
        });
        let mut h = blake3::Hasher::new();
        h.update(b"nuxiva.memory.sighting|");
        h.update(self.camera.as_bytes());
        h.update(&self.start.to_be_bytes());
        h.update(self.track.as_deref().unwrap_or("").as_bytes());
        h.update(&[self.class as u8]);
        let id = h.finalize().as_bytes().iter().take(16).fold(
            String::with_capacity(32),
            |mut out, b| {
                use std::fmt::Write as _;
                let _ = write!(out, "{b:02x}");
                out
            },
        );
        let mean = (self.score / seen as f32).clamp(0.0, 1.0);
        let support = (seen as f32 / 3.0).min(1.0);
        Sighting {
            id,
            start_ms: self.start,
            end_ms: self.last,
            camera: self.camera,
            zone: self.zone,
            class: self.class,
            who,
            look: Look {
                upper: self.upper.winner(0.5),
                lower: self.lower.winner(0.5),
                headwear: self.headwear.winner(0.5),
                face_covered,
                glasses,
                beard,
                hi_vis,
                build: self.build.winner(0.5),
                height_cm: self.heights.get(self.heights.len() / 2).copied(),
                carrying,
            },
            vehicle,
            gait: Vec::new(),
            evidence: self.evidence,
            confidence: (mean * (0.5 + 0.5 * support)).clamp(0.0, 1.0),
            pinned: false,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Assembler {
    idle_ms: u64,
    max_span_ms: u64,
    open: Vec<Open>,
}

impl Assembler {
    #[must_use]
    pub fn new(idle_ms: u64, max_span_ms: u64) -> Self {
        Self {
            idle_ms: idle_ms.clamp(1_000, 600_000),
            max_span_ms: max_span_ms.clamp(10_000, crate::sighting::MAX_SPAN_MS),
            open: Vec::new(),
        }
    }

    pub fn push(&mut self, o: &Observation) -> Result<Vec<Sighting>, MemoryError> {
        o.validate()?;
        let best = self
            .open
            .iter()
            .enumerate()
            .filter_map(|(i, s)| s.fits(o, self.idle_ms).map(|score| (i, score)))
            .max_by(|a, b| a.1.total_cmp(&b.1))
            .map(|(i, _)| i);
        let mut done = Vec::new();
        if let Some(slot) = best.and_then(|i| self.open.get_mut(i)) {
            slot.absorb(o);
            return Ok(done);
        }
        if self.open.len() >= MAX_OPEN {
            let oldest = self
                .open
                .iter()
                .enumerate()
                .min_by_key(|(_, s)| s.last)
                .map(|(i, _)| i);
            if let Some(i) = oldest {
                done.push(self.open.swap_remove(i).finish());
            }
        }
        let mut fresh = Open::new(o);
        fresh.absorb(o);
        self.open.push(fresh);
        Ok(done)
    }

    pub fn flush(&mut self, now_ms: u64) -> Vec<Sighting> {
        let (idle, span) = (self.idle_ms, self.max_span_ms);
        let (gone, keep): (Vec<Open>, Vec<Open>) =
            std::mem::take(&mut self.open).into_iter().partition(|s| {
                now_ms.saturating_sub(s.last) > idle || s.last.saturating_sub(s.start) >= span
            });
        self.open = keep;
        gone.into_iter().map(Open::finish).collect()
    }

    pub fn drain(&mut self) -> Vec<Sighting> {
        std::mem::take(&mut self.open)
            .into_iter()
            .map(Open::finish)
            .collect()
    }

    #[must_use]
    pub fn open_count(&self) -> usize {
        self.open.len()
    }
}
