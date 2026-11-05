use serde::{Deserialize, Serialize};

use crate::error::ForesightError;
use crate::num::{count, mean, round3};
use crate::report::{Leaning, leaning};
use crate::rng::mix;
use crate::spec::ScenarioSpec;
use crate::world::{World, work};

pub const MAX_RUNS: u16 = 64;
const MAX_ENSEMBLE_WORK: u64 = 2_400_000;

#[derive(Debug, Clone, Copy, Default, PartialEq, Serialize, Deserialize)]
pub struct Ensemble {
    pub runs: u16,
    pub support: u16,
    pub oppose: u16,
    pub divided: u16,
    pub undecided: u16,
    pub mean: f64,
    pub low: f64,
    pub median: f64,
    pub high: f64,
    pub polarization: f64,
}

fn quantile(sorted: &[f64], q: f64) -> f64 {
    let last = sorted.len().saturating_sub(1);
    let position = (count(last) * q).round();
    let index = (0..=last).find(|i| count(*i) >= position).unwrap_or(last);
    sorted.get(index).copied().unwrap_or(0.0)
}

pub fn ensemble(spec: &ScenarioSpec, runs: u16) -> Result<Ensemble, ForesightError> {
    if runs == 0 || runs > MAX_RUNS {
        return Err(ForesightError::Limit("runs"));
    }
    spec.validate()?;
    let total = work(spec)?
        .checked_mul(u64::from(runs))
        .ok_or(ForesightError::Limit("work"))?;
    if total > MAX_ENSEMBLE_WORK {
        return Err(ForesightError::Limit("work"));
    }
    let mut out = Ensemble {
        runs,
        ..Ensemble::default()
    };
    let mut finals = Vec::with_capacity(usize::from(runs));
    let mut polarization = 0.0;
    let mut seed = spec.seed;
    for _ in 0..runs {
        seed = mix(seed);
        let mut variant = spec.clone();
        variant.seed = seed;
        let mut world = World::new(variant)?;
        world.advance(spec.rounds);
        let Some(last) = world.latest().copied() else {
            continue;
        };
        let slot = match leaning(&last) {
            Leaning::Support => &mut out.support,
            Leaning::Oppose => &mut out.oppose,
            Leaning::Divided => &mut out.divided,
            Leaning::Undecided => &mut out.undecided,
        };
        *slot = slot.saturating_add(1);
        polarization += last.polarization;
        finals.push(last.mean);
    }
    finals.sort_by(f64::total_cmp);
    out.mean = round3(mean(finals.iter().sum(), finals.len()));
    out.low = round3(quantile(&finals, 0.1));
    out.median = round3(quantile(&finals, 0.5));
    out.high = round3(quantile(&finals, 0.9));
    out.polarization = round3(mean(polarization, finals.len()));
    Ok(out)
}
