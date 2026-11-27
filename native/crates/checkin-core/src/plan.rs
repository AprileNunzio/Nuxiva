use std::collections::{BTreeMap, BTreeSet};

use serde::Serialize;

use crate::error::CheckinResult;
use crate::model::{Fact, Kind, Moment, Request, Turn};
use crate::text::{similar, words};

pub const URGENT: u8 = 65;
pub const MIN_UTILITY: f64 = 0.12;
pub const REUSE_WINDOW: i64 = 600;
pub const OK_FRESH: i64 = 1_200;
const TOPIC_DECAY: f64 = 0.6;
const HUMOR_WINDOW: usize = 6;
const HUMOR_MAX: usize = 2;
const STYLE_MEMORY: usize = 2;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Daypart {
    Night,
    Morning,
    Afternoon,
    Evening,
    Late,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Tone {
    Quiet,
    Formal,
    Warm,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Chosen {
    pub key: String,
    pub signature: String,
    pub topic: String,
    pub kind: Kind,
    pub utility: f64,
    pub repeat: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Plan {
    pub facts: Vec<Chosen>,
    pub verified: Vec<String>,
    pub verified_again: bool,
    pub stale: Vec<String>,
    pub daypart: Daypart,
    pub tone: Tone,
    pub humor: bool,
    pub style: &'static str,
    pub budget: usize,
    pub reuse: bool,
}

#[must_use]
pub fn daypart(hour: u8) -> Daypart {
    match hour {
        0..=5 => Daypart::Night,
        6..=11 => Daypart::Morning,
        12..=17 => Daypart::Afternoon,
        18..=22 => Daypart::Evening,
        _ => Daypart::Late,
    }
}

fn seconds(a: i64, b: i64) -> f64 {
    let d = a.saturating_sub(b).max(0);
    f64::from(u32::try_from(d).unwrap_or(u32::MAX))
}

fn timeliness(kind: Kind, part: Daypart) -> f64 {
    match (kind, part) {
        (Kind::Agenda, Daypart::Morning) | (Kind::Interest, Daypart::Evening) => 1.2,
        (Kind::Info, Daypart::Morning) => 1.1,
        (Kind::Interest | Kind::Info, Daypart::Night | Daypart::Late) => 0.4,
        (Kind::Agenda, Daypart::Night) => 0.5,
        _ => 1.0,
    }
}

fn proximity(fact: &Fact, now: i64) -> f64 {
    let Some(start) = fact.starts_at else {
        return 1.0;
    };
    if start >= now {
        let hours = seconds(start, now) / 3_600.0;
        if hours <= 12.0 {
            1.0 + 0.5 * (1.0 - hours / 12.0)
        } else {
            0.7
        }
    } else if seconds(now, start) <= 3.0 * 3_600.0 {
        1.3
    } else {
        0.3
    }
}

fn last_told(history: &[Turn], signature: &str) -> Option<i64> {
    history
        .iter()
        .filter(|t| t.told.iter().any(|s| s == signature))
        .map(|t| t.at)
        .max()
}

fn novelty(fact: &Fact, history: &[Turn], now: i64) -> f64 {
    last_told(history, &fact.signature).map_or(1.0, |at| {
        1.0 - 0.5_f64.powf(seconds(now, at) / fact.kind.half_life())
    })
}

fn focused(fact: &Fact, focus: &[String]) -> bool {
    let mine: Vec<String> = fact
        .terms
        .iter()
        .chain(std::iter::once(&fact.topic))
        .flat_map(|t| words(t))
        .collect();
    focus
        .iter()
        .flat_map(|f| words(f))
        .any(|f| mine.iter().any(|m| similar(m, &f)))
}

fn utility(fact: &Fact, req: &Request, part: Daypart) -> (f64, bool) {
    let now = req.moment.now;
    let fresh = novelty(fact, &req.history, now);
    let urgent = fact.kind == Kind::Alert && fact.priority >= URGENT;
    let novelty = if urgent { fresh.max(0.5) } else { fresh };
    let lead = if focused(fact, &req.focus) { 1.0 } else { 0.0 };
    let value = f64::from(fact.priority) / 100.0
        * novelty
        * timeliness(fact.kind, part)
        * proximity(fact, now);
    (value + lead, fresh < 0.5)
}

fn budget(part: Daypart, voice: bool, focus: bool) -> usize {
    let base: usize = match part {
        Daypart::Night | Daypart::Late => 2,
        _ if voice => 3,
        _ => 4,
    };
    if focus { base.saturating_add(1) } else { base }
}

fn select(req: &Request, live: &[&Fact], part: Daypart) -> Vec<Chosen> {
    let limit = budget(part, req.voice, !req.focus.is_empty());
    let mut pool: Vec<(&Fact, f64, bool)> = live
        .iter()
        .filter(|f| f.kind != Kind::Ok)
        .map(|f| {
            let (u, repeat) = utility(f, req, part);
            (*f, u, repeat)
        })
        .collect();
    let mut chosen: Vec<Chosen> = Vec::new();
    let mut per_topic: BTreeMap<String, i32> = BTreeMap::new();
    while chosen.len() < limit {
        let best = pool
            .iter()
            .enumerate()
            .map(|(i, (f, u, _))| {
                let seen = per_topic.get(&f.topic).copied().unwrap_or(0);
                (i, u * TOPIC_DECAY.powi(seen))
            })
            .filter(|(_, u)| *u >= MIN_UTILITY)
            .max_by(|a, b| a.1.total_cmp(&b.1));
        let Some((index, score)) = best else { break };
        let (fact, _, repeat) = pool.swap_remove(index);
        let slot = per_topic.entry(fact.topic.clone()).or_insert(0);
        *slot = slot.saturating_add(1);
        chosen.push(Chosen {
            key: fact.key.clone(),
            signature: fact.signature.clone(),
            topic: fact.topic.clone(),
            kind: fact.kind,
            utility: (score * 1000.0).round() / 1000.0,
            repeat,
        });
    }
    chosen
}

fn humor(req: &Request, tone: Tone, part: Daypart) -> bool {
    if tone != Tone::Warm || matches!(part, Daypart::Night | Daypart::Late) {
        return false;
    }
    let recent = req
        .history
        .iter()
        .rev()
        .take(HUMOR_WINDOW)
        .filter(|t| t.humor)
        .count();
    recent < HUMOR_MAX && req.seed.checked_rem(2) == Some(0)
}

fn style(req: &Request, tone: Tone, humor: bool) -> &'static str {
    let options: &[&'static str] = match tone {
        Tone::Quiet => &["soft", "brief"],
        Tone::Formal => &["direct", "reassure"],
        Tone::Warm if humor => &["playful", "personal", "curious"],
        Tone::Warm => &["personal", "reassure", "curious", "direct"],
    };
    let mut ordered: Vec<&Turn> = req.history.iter().collect();
    ordered.sort_by_key(|t| t.at);
    let blocked: BTreeSet<&str> = ordered
        .iter()
        .rev()
        .take(STYLE_MEMORY)
        .map(|t| t.style.as_str())
        .collect();
    let used_at = |s: &str| {
        ordered
            .iter()
            .filter(|t| t.style == s)
            .map(|t| t.at)
            .max()
            .unwrap_or(i64::MIN)
    };
    let free: Vec<&'static str> = options
        .iter()
        .copied()
        .filter(|s| !blocked.contains(s))
        .collect();
    let candidates = if free.is_empty() {
        options.to_vec()
    } else {
        free
    };
    let oldest = candidates
        .iter()
        .map(|s| used_at(s))
        .min()
        .unwrap_or(i64::MIN);
    let ties: Vec<&'static str> = candidates
        .into_iter()
        .filter(|s| used_at(s) == oldest)
        .collect();
    let len = u64::try_from(ties.len().max(1)).unwrap_or(1);
    let pick = usize::try_from(req.seed.checked_rem(len).unwrap_or(0)).unwrap_or(0);
    ties.get(pick).copied().unwrap_or("direct")
}

fn reused(req: &Request, chosen: &[Chosen]) -> bool {
    let Some(last) = req.history.iter().max_by_key(|t| t.at) else {
        return false;
    };
    req.moment.now.saturating_sub(last.at) <= REUSE_WINDOW
        && req.focus.is_empty()
        && chosen.iter().all(|c| c.kind != Kind::Alert)
        && chosen.iter().all(|c| last.told.contains(&c.signature))
}

fn verified(req: &Request, live: &[&Fact]) -> (Vec<String>, bool) {
    let oks: Vec<&&Fact> = live.iter().filter(|f| f.kind == Kind::Ok).collect();
    let topics: BTreeSet<String> = oks.iter().map(|f| f.topic.clone()).collect();
    let again = !oks.is_empty()
        && oks.iter().all(|f| {
            last_told(&req.history, &f.signature)
                .is_some_and(|at| req.moment.now.saturating_sub(at) <= OK_FRESH)
        });
    (topics.into_iter().collect(), again)
}

fn alive(fact: &Fact, moment: Moment) -> bool {
    moment.now.saturating_sub(fact.observed_at) <= fact.ttl.max(0)
}

pub fn plan(req: &Request) -> CheckinResult<Plan> {
    req.validate()?;
    let part = daypart(req.moment.hour);
    let (live, dead): (Vec<&Fact>, Vec<&Fact>) =
        req.facts.iter().partition(|f| alive(f, req.moment));
    let chosen = select(req, &live, part);
    let alert = chosen.iter().any(|c| c.kind == Kind::Alert);
    let tone = if alert {
        Tone::Formal
    } else if matches!(part, Daypart::Night | Daypart::Late) {
        Tone::Quiet
    } else {
        Tone::Warm
    };
    let humor = humor(req, tone, part);
    let (verified, verified_again) = verified(req, &live);
    Ok(Plan {
        reuse: reused(req, &chosen),
        style: style(req, tone, humor),
        budget: budget(part, req.voice, !req.focus.is_empty()),
        facts: chosen,
        verified,
        verified_again,
        stale: dead.iter().map(|f| f.key.clone()).collect(),
        daypart: part,
        tone,
        humor,
    })
}
