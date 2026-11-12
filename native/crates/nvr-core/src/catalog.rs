use std::collections::{BTreeMap, HashMap};
use std::ops::Bound::{Excluded, Included, Unbounded};

use serde::{Deserialize, Serialize};

use crate::error::{NvrError, NvrResult};
use crate::segment::{Segment, Tier, valid_id};

pub const MAX_SEGMENTS: usize = 4_000_000;
const LOOK_BACK: usize = 8;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Seek {
    pub segment: Segment,
    pub offset_ms: u64,
    pub gap_ms: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CameraSummary {
    pub camera: String,
    pub segments: usize,
    pub bytes: u64,
    pub first_ms: u64,
    pub last_ms: u64,
    pub audio_segments: usize,
}

#[derive(Debug, Default, Clone)]
pub struct Catalog {
    cameras: BTreeMap<String, BTreeMap<u64, Segment>>,
    ids: HashMap<(String, String), u64>,
}

impl Catalog {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn len(&self) -> usize {
        self.ids.len()
    }

    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.ids.is_empty()
    }

    pub fn insert(&mut self, segment: Segment) -> NvrResult<()> {
        segment.validate()?;
        let key = (segment.camera.clone(), segment.id.clone());
        if !self.ids.contains_key(&key) && self.ids.len() >= MAX_SEGMENTS {
            return Err(NvrError::TooMany);
        }
        self.remove(&segment.camera, &segment.id);
        let start = segment.start_ms;
        let line = self.cameras.entry(segment.camera.clone()).or_default();
        if let Some(previous) = line.insert(start, segment) {
            self.ids.remove(&(previous.camera, previous.id));
        }
        self.ids.insert(key, start);
        Ok(())
    }

    pub fn remove(&mut self, camera: &str, id: &str) -> Option<Segment> {
        let start = self.ids.remove(&(camera.to_owned(), id.to_owned()))?;
        let line = self.cameras.get_mut(camera)?;
        let gone = line.remove(&start);
        if line.is_empty() {
            self.cameras.remove(camera);
        }
        gone
    }

    #[must_use]
    pub fn get(&self, camera: &str, id: &str) -> Option<&Segment> {
        let start = self.ids.get(&(camera.to_owned(), id.to_owned()))?;
        self.cameras.get(camera)?.get(start)
    }

    pub fn set_tier(&mut self, camera: &str, id: &str, tier: Tier) -> NvrResult<()> {
        let start = *self
            .ids
            .get(&(camera.to_owned(), id.to_owned()))
            .ok_or(NvrError::NotFound)?;
        let segment = self
            .cameras
            .get_mut(camera)
            .and_then(|line| line.get_mut(&start))
            .ok_or(NvrError::NotFound)?;
        segment.tier = tier;
        Ok(())
    }

    pub fn range(
        &self,
        camera: &str,
        from_ms: u64,
        to_ms: u64,
        limit: usize,
    ) -> NvrResult<Vec<Segment>> {
        if !valid_id(camera) {
            return Err(NvrError::InvalidId);
        }
        let Some(line) = self.cameras.get(camera) else {
            return Ok(Vec::new());
        };
        if to_ms <= from_ms || limit == 0 {
            return Ok(Vec::new());
        }
        let mut before: Vec<&Segment> = line
            .range((Unbounded, Included(from_ms)))
            .rev()
            .take(LOOK_BACK)
            .map(|(_, s)| s)
            .filter(|s| s.overlaps(from_ms, to_ms))
            .collect();
        before.reverse();
        let after = line
            .range((Excluded(from_ms), Excluded(to_ms)))
            .map(|(_, s)| s);
        Ok(before
            .into_iter()
            .chain(after)
            .take(limit)
            .cloned()
            .collect())
    }

    #[must_use]
    pub fn seek(&self, camera: &str, at_ms: u64) -> Option<Seek> {
        let line = self.cameras.get(camera)?;
        let holding = line
            .range((Unbounded, Included(at_ms)))
            .rev()
            .take(LOOK_BACK)
            .map(|(_, s)| s)
            .find(|s| s.end_ms() > at_ms);
        if let Some(segment) = holding {
            return Some(Seek {
                segment: segment.clone(),
                offset_ms: at_ms.saturating_sub(segment.start_ms),
                gap_ms: 0,
            });
        }
        let (_, next) = line.range((Excluded(at_ms), Unbounded)).next()?;
        Some(Seek {
            segment: next.clone(),
            offset_ms: 0,
            gap_ms: next.start_ms.saturating_sub(at_ms),
        })
    }

    #[must_use]
    pub fn after(&self, camera: &str, id: &str) -> Option<&Segment> {
        let start = self.ids.get(&(camera.to_owned(), id.to_owned()))?;
        self.cameras
            .get(camera)?
            .range((Excluded(*start), Unbounded))
            .next()
            .map(|(_, s)| s)
    }

    pub fn iter(&self) -> impl Iterator<Item = &Segment> {
        self.cameras.values().flat_map(BTreeMap::values)
    }

    #[must_use]
    pub fn camera_segments(&self, camera: &str) -> Vec<Segment> {
        self.cameras
            .get(camera)
            .map(|line| line.values().cloned().collect())
            .unwrap_or_default()
    }

    #[must_use]
    pub fn total_bytes(&self) -> u64 {
        self.iter().fold(0u64, |acc, s| acc.saturating_add(s.bytes))
    }

    #[must_use]
    pub fn summary(&self) -> Vec<CameraSummary> {
        self.cameras
            .iter()
            .map(|(camera, line)| CameraSummary {
                camera: camera.clone(),
                segments: line.len(),
                bytes: line
                    .values()
                    .fold(0u64, |acc, s| acc.saturating_add(s.bytes)),
                first_ms: line.values().next().map_or(0, |s| s.start_ms),
                last_ms: line.values().map(Segment::end_ms).max().unwrap_or(0),
                audio_segments: line.values().filter(|s| s.audio).count(),
            })
            .collect()
    }

    pub fn to_json(&self) -> NvrResult<String> {
        let all: Vec<&Segment> = self.iter().collect();
        serde_json::to_string(&all).map_err(|e| NvrError::Serialization(e.to_string()))
    }

    pub fn from_json(text: &str) -> NvrResult<Self> {
        let rows: Vec<Segment> =
            serde_json::from_str(text).map_err(|e| NvrError::Serialization(e.to_string()))?;
        if rows.len() > MAX_SEGMENTS {
            return Err(NvrError::TooMany);
        }
        let mut catalog = Self::new();
        for row in rows {
            catalog.insert(row)?;
        }
        Ok(catalog)
    }
}
