use serde::{Deserialize, Serialize};

pub const TIERS: u8 = 10;
pub const MAX_ATTEMPTS: usize = 400;
pub const WINDOW: usize = 5;
pub const PASS_MIN: usize = 3;
pub const PASS_MEAN: f64 = 0.7;
pub const STALE_SECS: i64 = 30 * 86_400;
pub const LAPSE_SECS: i64 = 90 * 86_400;

#[derive(Debug, Clone, Copy, Deserialize, Serialize)]
pub struct Attempt {
    pub tier: u8,
    pub score: f64,
    pub at: i64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NextKind {
    Advance,
    Review,
    Maintain,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct Next {
    pub tier: u8,
    pub kind: NextKind,
}

#[derive(Debug, Clone, Serialize)]
pub struct Standing {
    pub level: u8,
    pub rank: &'static str,
    pub attempts: usize,
    pub recent_mean: f64,
    pub next: Next,
}

#[must_use]
pub fn rank(level: u8) -> &'static str {
    match level {
        0 => "novice",
        1..=2 => "apprentice",
        3..=4 => "proficient",
        5..=6 => "advanced",
        7..=8 => "expert",
        _ => "master",
    }
}

fn clean(raw: &[Attempt]) -> Vec<Attempt> {
    let skip = raw.len().saturating_sub(MAX_ATTEMPTS);
    raw.iter()
        .skip(skip)
        .filter(|a| a.tier < TIERS)
        .map(|a| Attempt {
            tier: a.tier,
            score: if a.score.is_finite() {
                a.score.clamp(0.0, 1.0)
            } else {
                0.0
            },
            at: a.at,
        })
        .collect()
}

fn window(list: &[Attempt], tier: u8) -> Vec<Attempt> {
    let mut found: Vec<Attempt> = list.iter().filter(|a| a.tier == tier).copied().collect();
    let skip = found.len().saturating_sub(WINDOW);
    found.drain(..skip);
    found
}

fn mean(list: &[Attempt]) -> f64 {
    if list.is_empty() {
        return 0.0;
    }
    let total: f64 = list.iter().map(|a| a.score).sum();
    total / f64::from(u32::try_from(list.len()).unwrap_or(u32::MAX))
}

fn latest(list: &[Attempt]) -> i64 {
    list.iter().map(|a| a.at).max().unwrap_or(i64::MIN)
}

fn passed(list: &[Attempt], tier: u8, now: i64) -> Option<i64> {
    let recent = window(list, tier);
    let last = latest(&recent);
    let fresh = now.saturating_sub(last) <= LAPSE_SECS;
    (recent.len() >= PASS_MIN && mean(&recent) >= PASS_MEAN && fresh).then_some(last)
}

#[must_use]
pub fn evaluate(raw: &[Attempt], now: i64) -> Standing {
    let list = clean(raw);
    let mut stamps: Vec<i64> = Vec::new();
    for tier in 0..TIERS {
        match passed(&list, tier, now) {
            Some(at) => stamps.push(at),
            None => break,
        }
    }
    let level = u8::try_from(stamps.len()).unwrap_or(TIERS);
    let stale = stamps
        .iter()
        .enumerate()
        .filter(|(_, at)| now.saturating_sub(**at) > STALE_SECS)
        .min_by_key(|(_, at)| **at);
    let next = if let Some((tier, _)) = stale {
        Next {
            tier: u8::try_from(tier).unwrap_or(0),
            kind: NextKind::Review,
        }
    } else if level >= TIERS {
        Next {
            tier: TIERS.saturating_sub(1),
            kind: NextKind::Maintain,
        }
    } else {
        Next {
            tier: level,
            kind: NextKind::Advance,
        }
    };
    let skip = list.len().saturating_sub(WINDOW);
    let tail: Vec<Attempt> = list.iter().skip(skip).copied().collect();
    Standing {
        level,
        rank: rank(level),
        attempts: list.len(),
        recent_mean: mean(&tail),
        next,
    }
}
