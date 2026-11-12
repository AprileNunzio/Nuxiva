use crate::rng::Rng;
use crate::spec::Traits;

const BACKFIRE: f64 = 0.6;
const READ_WEIGHT_MIN: f64 = 0.05;
const READ_WEIGHT_MAX: f64 = 2.5;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Exposure {
    pub post: Option<u64>,
    pub author: Option<usize>,
    pub event: Option<usize>,
    pub stance: f64,
    pub weight: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Choice {
    Like,
    Repost,
    Reply,
    Post,
    Quiet,
}

#[must_use]
pub fn weight(influence: f64, followed: bool, affinity: f64) -> f64 {
    let trust = if followed { 1.0 } else { 0.6 };
    ((0.4 + influence) * trust * (1.0 + 0.5 * affinity)).clamp(READ_WEIGHT_MIN, READ_WEIGHT_MAX)
}

#[must_use]
pub fn agreement(a: f64, b: f64) -> f64 {
    (1.0 - (a - b).abs() / 2.0).clamp(0.0, 1.0)
}

#[must_use]
pub fn update(current: f64, traits: &Traits, exposures: &[Exposure]) -> f64 {
    let tolerance = 0.25 + 0.75 * traits.openness;
    let rate = 0.35 * (1.0 - traits.stubbornness);
    let mut pull = 0.0;
    let mut total = 0.0;
    for exposure in exposures {
        let gap = exposure.stance - current;
        total += exposure.weight;
        if gap.abs() <= tolerance {
            pull += exposure.weight * rate * gap;
        } else if traits.stubbornness > BACKFIRE {
            let excess = (gap.abs() - tolerance).min(1.0);
            pull -=
                exposure.weight * (traits.stubbornness - BACKFIRE) * 0.25 * gap.signum() * excess;
        }
    }
    if total <= f64::EPSILON {
        return current;
    }
    (current + pull / total.max(1.0)).clamp(-1.0, 1.0)
}

pub fn choose(rng: &mut Rng, agree: f64) -> Choice {
    let roll = rng.unit();
    if agree > 0.85 {
        if roll < 0.3 {
            return Choice::Repost;
        }
        if roll < 0.65 {
            return Choice::Like;
        }
    } else if agree < 0.55 && roll < 0.5 {
        return Choice::Reply;
    }
    if rng.unit() < 0.55 {
        Choice::Post
    } else {
        Choice::Quiet
    }
}
