use std::collections::BTreeMap;

use serde::Serialize;

use crate::look::{Color, Headwear, Item};
use crate::sighting::Sighting;

pub const TOP: usize = 3;

#[derive(Debug, Clone, Default, PartialEq, Serialize)]
pub struct Profile {
    pub count: usize,
    pub first_ms: Option<u64>,
    pub last_ms: Option<u64>,
    pub upper: Vec<(Color, usize)>,
    pub lower: Vec<(Color, usize)>,
    pub headwear: Vec<(Headwear, usize)>,
    pub items: Vec<(Item, usize)>,
    pub cameras: Vec<(String, usize)>,
    pub height_cm: Option<u16>,
    pub glasses: Option<f32>,
    pub face_covered: usize,
    pub gait_samples: usize,
    pub gait_signature: Option<Vec<f32>>,
}

fn top<K: Ord + Clone>(counts: BTreeMap<K, usize>) -> Vec<(K, usize)> {
    let mut list: Vec<(K, usize)> = counts.into_iter().collect();
    list.sort_by(|a, b| b.1.cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    list.truncate(TOP);
    list
}

fn bump<K: Ord>(map: &mut BTreeMap<K, usize>, key: K) {
    let slot = map.entry(key).or_insert(0);
    *slot = slot.saturating_add(1);
}

#[must_use]
#[allow(clippy::cast_precision_loss)]
pub fn build<'a>(sightings: impl IntoIterator<Item = &'a Sighting>) -> Profile {
    let mut out = Profile::default();
    let (mut upper, mut lower, mut head, mut items, mut cams) = (
        BTreeMap::new(),
        BTreeMap::new(),
        BTreeMap::new(),
        BTreeMap::new(),
        BTreeMap::new(),
    );
    let mut heights = Vec::new();
    let (mut seen_glasses, mut with_glasses) = (0_usize, 0_usize);
    let mut sum_gait = [0.0_f32; 16];
    for s in sightings {
        out.count = out.count.saturating_add(1);
        out.first_ms = Some(out.first_ms.map_or(s.start_ms, |f| f.min(s.start_ms)));
        out.last_ms = Some(out.last_ms.map_or(s.end_ms, |l| l.max(s.end_ms)));
        let look = &s.look;
        if let Some(c) = look.upper {
            bump(&mut upper, c);
        }
        if let Some(c) = look.lower {
            bump(&mut lower, c);
        }
        if let Some(h) = look.headwear {
            bump(&mut head, h);
        }
        for i in &look.carrying {
            bump(&mut items, *i);
        }
        bump(&mut cams, s.camera.clone());
        if let Some(h) = look.height_cm {
            heights.push(h);
        }
        if let Some(g) = look.glasses {
            seen_glasses = seen_glasses.saturating_add(1);
            with_glasses = with_glasses.saturating_add(usize::from(g));
        }
        if look.face_covered == Some(true) {
            out.face_covered = out.face_covered.saturating_add(1);
        }
        if s.gait.len() == 16 {
            out.gait_samples = out.gait_samples.saturating_add(1);
            for (idx, val) in s.gait.iter().enumerate() {
                if let Some(slot) = sum_gait.get_mut(idx) {
                    *slot += *val;
                }
            }
        }
    }
    heights.sort_unstable();
    out.height_cm = heights.get(heights.len() / 2).copied();
    out.glasses = (seen_glasses > 0).then(|| with_glasses as f32 / seen_glasses as f32);
    out.upper = top(upper);
    out.lower = top(lower);
    out.headwear = top(head);
    out.items = top(items);
    out.cameras = top(cams);
    if out.gait_samples > 0 {
        #[allow(clippy::cast_precision_loss)]
        let count_f = out.gait_samples as f32;
        let mut avg = vec![0.0_f32; 16];
        for (idx, val) in sum_gait.iter().enumerate() {
            if let Some(slot) = avg.get_mut(idx) {
                *slot = *val / count_f;
            }
        }
        out.gait_signature = Some(avg);
    }
    out
}
