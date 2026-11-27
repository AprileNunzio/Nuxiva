use serde::{Deserialize, Serialize};

use crate::error::{CheckinError, CheckinResult};
use crate::model::MAX_FIELD;
use crate::plan::{Daypart, daypart};
use crate::text::{similar, words};

pub const OBSERVE_WINDOW: i64 = 180;
pub const MIN_WEIGHT: f64 = 0.4;
pub const MAX_WEIGHT: f64 = 1.8;
pub const MAX_ENTRIES: usize = 256;
const ENGAGED: f64 = 1.6;
const IGNORED: f64 = 0.85;
const REJECTED: f64 = 0.6;
const MIN_RATE: f64 = 0.1;
const ANY: &str = "any";

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct Entry {
    pub topic: String,
    pub when: String,
    pub weight: f64,
    pub samples: u32,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct Told {
    pub topic: String,
    #[serde(default)]
    pub terms: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Observe {
    pub at: i64,
    pub now: i64,
    pub hour: u8,
    pub reply: String,
    #[serde(default)]
    pub told: Vec<Told>,
    #[serde(default)]
    pub interrupted: bool,
    #[serde(default)]
    pub affinity: Vec<Entry>,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct Observation {
    pub counted: bool,
    pub engaged: Vec<String>,
    pub ignored: Vec<String>,
    pub affinity: Vec<Entry>,
}

fn part_name(part: Daypart) -> &'static str {
    match part {
        Daypart::Night => "night",
        Daypart::Morning => "morning",
        Daypart::Afternoon => "afternoon",
        Daypart::Evening => "evening",
        Daypart::Late => "late",
    }
}

fn find<'a>(entries: &'a [Entry], topic: &str, when: &str) -> Option<&'a Entry> {
    entries.iter().find(|e| e.topic == topic && e.when == when)
}

#[must_use]
pub fn weight(entries: &[Entry], topic: &str, part: Daypart) -> f64 {
    let specific = find(entries, topic, part_name(part));
    let general = find(entries, topic, ANY);
    let blended = match (specific, general) {
        (Some(s), Some(g)) => {
            let trust = f64::from(s.samples.min(10)) / 10.0;
            trust * s.weight + (1.0 - trust) * g.weight
        }
        (None, Some(g)) => g.weight,
        (Some(s), None) => s.weight,
        (None, None) => 1.0,
    };
    blended.clamp(MIN_WEIGHT, MAX_WEIGHT)
}

fn learn(entries: &mut Vec<Entry>, topic: &str, when: &str, target: f64, strength: f64) {
    let index = entries
        .iter()
        .position(|e| e.topic == topic && e.when == when);
    let index = index.unwrap_or_else(|| {
        entries.push(Entry {
            topic: topic.to_owned(),
            when: when.to_owned(),
            weight: 1.0,
            samples: 0,
        });
        entries.len().saturating_sub(1)
    });
    if let Some(e) = entries.get_mut(index) {
        let rate = (1.0 / (f64::from(e.samples) + 3.0)).max(MIN_RATE) * strength;
        e.weight = (e.weight + rate * (target - e.weight)).clamp(MIN_WEIGHT, MAX_WEIGHT);
        e.weight = (e.weight * 1000.0).round() / 1000.0;
        e.samples = e.samples.saturating_add(1);
    }
}

fn mentions(told: &Told, reply: &[String]) -> bool {
    told.terms
        .iter()
        .chain(std::iter::once(&told.topic))
        .flat_map(|t| words(t))
        .filter(|t| t.chars().count() >= 3)
        .any(|t| reply.iter().any(|w| similar(w, &t)))
}

fn check(request: &Observe) -> CheckinResult<()> {
    if request.reply.len() > 600 || request.told.len() > 64 || request.affinity.len() > MAX_ENTRIES
    {
        return Err(CheckinError::TooLarge("observe"));
    }
    if request.hour > 23 {
        return Err(CheckinError::Invalid("hour".to_owned()));
    }
    let long = |s: &String| s.len() > MAX_FIELD;
    let told = request
        .told
        .iter()
        .any(|t| long(&t.topic) || t.terms.len() > 16 || t.terms.iter().any(long));
    let known = request
        .affinity
        .iter()
        .any(|e| long(&e.topic) || long(&e.when) || !e.weight.is_finite());
    if told || known {
        return Err(CheckinError::Invalid("observe fields".to_owned()));
    }
    Ok(())
}

pub fn observe(request: &Observe) -> CheckinResult<Observation> {
    check(request)?;
    let mut affinity = request.affinity.clone();
    let elapsed = request.now.saturating_sub(request.at);
    if request.told.is_empty() || !(0..=OBSERVE_WINDOW).contains(&elapsed) {
        return Ok(Observation {
            counted: false,
            engaged: Vec::new(),
            ignored: Vec::new(),
            affinity,
        });
    }
    let reply = words(&request.reply);
    let when = part_name(daypart(request.hour));
    let (mut engaged, mut ignored) = (Vec::new(), Vec::new());
    for told in &request.told {
        let (target, strength) = if request.interrupted {
            (REJECTED, 1.0)
        } else if mentions(told, &reply) {
            (ENGAGED, 1.0)
        } else {
            (IGNORED, 0.5)
        };
        if target > 1.0 {
            engaged.push(told.topic.clone());
        } else {
            ignored.push(told.topic.clone());
        }
        learn(&mut affinity, &told.topic, when, target, strength);
        learn(&mut affinity, &told.topic, ANY, target, strength * 0.5);
    }
    affinity.truncate(MAX_ENTRIES);
    Ok(Observation {
        counted: true,
        engaged,
        ignored,
        affinity,
    })
}
