use serde::{Deserialize, Serialize};

use crate::round_to;

pub const NEAR_HOURS: usize = 12;
pub const DAY_HOURS: usize = 24;

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Hour {
    pub time: String,
    pub temp: Option<f64>,
    pub feels: Option<f64>,
    pub rain_prob: Option<f64>,
    pub rain: Option<f64>,
    pub gust: Option<f64>,
    pub uv: Option<f64>,
    pub code: Option<i64>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Day {
    pub tmax: Option<f64>,
    pub tmin: Option<f64>,
    pub uv: Option<f64>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Slot {
    pub time: String,
    pub rain: Option<f64>,
}

#[derive(Debug, Clone, Default, Deserialize)]
pub struct Situation {
    #[serde(default)]
    pub hourly: Vec<Hour>,
    #[serde(default)]
    pub days: Vec<Day>,
    #[serde(default)]
    pub yesterday: Option<Day>,
    #[serde(default)]
    pub nowcast: Vec<Slot>,
}

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "lowercase")]
pub enum Level {
    Info,
    Warn,
    Alert,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Insight {
    pub kind: &'static str,
    pub level: Level,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub value: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub time: Option<String>,
}

const WET_MM: f64 = 0.1;
const STORM: [i64; 3] = [95, 96, 99];
const SNOW: [i64; 7] = [71, 73, 75, 77, 85, 86, 66];
const FOG: [i64; 2] = [45, 48];

fn ok(value: Option<f64>) -> Option<f64> {
    value.filter(|v| v.is_finite())
}

fn peak<F: Fn(&Hour) -> Option<f64>>(hours: &[Hour], pick: F) -> Option<(f64, String)> {
    let mut best: Option<(f64, String)> = None;
    for hour in hours {
        if let Some(v) = ok(pick(hour)) {
            if best.as_ref().is_none_or(|(b, _)| v > *b) {
                best = Some((v, hour.time.clone()));
            }
        }
    }
    best
}

fn first_code(hours: &[Hour], codes: &[i64]) -> Option<String> {
    hours
        .iter()
        .find(|h| h.code.is_some_and(|c| codes.contains(&c)))
        .map(|h| h.time.clone())
}

fn push(
    out: &mut Vec<Insight>,
    kind: &'static str,
    level: Level,
    value: Option<f64>,
    time: Option<String>,
) {
    out.push(Insight {
        kind,
        level,
        value,
        time,
    });
}

fn yesterday(out: &mut Vec<Insight>, situation: &Situation) {
    let today = situation.days.first().and_then(|d| ok(d.tmax));
    let before = situation.yesterday.as_ref().and_then(|d| ok(d.tmax));
    if let (Some(now), Some(then)) = (today, before) {
        let delta = round_to(now - then, 1);
        let kind = if delta >= 1.0 {
            "warmer"
        } else if delta <= -1.0 {
            "colder"
        } else {
            "same"
        };
        push(out, kind, Level::Info, Some(delta), None);
    }
}

fn nowcast(out: &mut Vec<Insight>, slots: &[Slot]) {
    let wet = |s: &Slot| ok(s.rain).is_some_and(|r| r >= WET_MM);
    let Some(first) = slots.first() else { return };
    if wet(first) {
        if let Some(dry) = slots.iter().find(|s| !wet(s) && ok(s.rain).is_some()) {
            push(out, "rain_stops", Level::Info, None, Some(dry.time.clone()));
        } else {
            push(out, "raining", Level::Info, None, None);
        }
    } else if let Some(start) = slots.iter().find(|s| wet(s)) {
        let total = slots.iter().filter_map(|s| ok(s.rain)).sum::<f64>();
        push(
            out,
            "rain_soon",
            Level::Warn,
            Some(round_to(total, 1)),
            Some(start.time.clone()),
        );
    }
}

#[must_use]
pub fn insights(situation: &Situation) -> Vec<Insight> {
    let mut out = Vec::new();
    let day = situation
        .hourly
        .get(..DAY_HOURS.min(situation.hourly.len()))
        .unwrap_or_default();
    let near = situation
        .hourly
        .get(..NEAR_HOURS.min(situation.hourly.len()))
        .unwrap_or_default();
    yesterday(&mut out, situation);
    nowcast(&mut out, &situation.nowcast);
    if let Some(time) = first_code(day, &STORM) {
        push(&mut out, "storm", Level::Alert, None, Some(time));
    }
    if let Some(time) = first_code(day, &SNOW) {
        push(&mut out, "snow", Level::Warn, None, Some(time));
    }
    if let Some((prob, time)) = peak(near, |h| h.rain_prob) {
        if prob >= 50.0 {
            push(
                &mut out,
                "umbrella",
                if prob >= 80.0 {
                    Level::Warn
                } else {
                    Level::Info
                },
                Some(prob),
                Some(time),
            );
        }
    }
    if let Some((gust, time)) = peak(day, |h| h.gust) {
        if gust >= 50.0 {
            push(
                &mut out,
                "wind",
                if gust >= 75.0 {
                    Level::Alert
                } else {
                    Level::Warn
                },
                Some(round_to(gust, 0)),
                Some(time),
            );
        }
    }
    if let Some((feels, time)) = peak(day, |h| h.feels) {
        if feels >= 32.0 {
            push(
                &mut out,
                "heat",
                if feels >= 38.0 {
                    Level::Alert
                } else {
                    Level::Warn
                },
                Some(round_to(feels, 0)),
                Some(time),
            );
        }
    }
    let low = situation
        .days
        .iter()
        .take(2)
        .filter_map(|d| ok(d.tmin))
        .fold(f64::INFINITY, f64::min);
    if low.is_finite() && low <= 1.0 {
        push(
            &mut out,
            "frost",
            if low <= -5.0 {
                Level::Alert
            } else {
                Level::Warn
            },
            Some(round_to(low, 0)),
            None,
        );
    }
    if let Some(uv) = situation.days.first().and_then(|d| ok(d.uv)) {
        if uv >= 6.0 {
            push(
                &mut out,
                "uv",
                if uv >= 8.0 { Level::Alert } else { Level::Warn },
                Some(round_to(uv, 1)),
                None,
            );
        }
    }
    if let Some(time) = first_code(near, &FOG) {
        push(&mut out, "fog", Level::Info, None, Some(time));
    }
    out.sort_by_key(|i| std::cmp::Reverse(i.level));
    out
}
