use std::collections::VecDeque;

use serde::{Deserialize, Serialize};

pub const ON: f32 = 0.6;
pub const OFF: f32 = 0.35;
pub const STREAK: u32 = 6;
pub const MIN_SEEN: u32 = 8;
pub const ALPHA: f32 = 0.2;
pub const SMOKE_HIT: f32 = 0.34;
pub const SMOKE_GAP_S: f64 = 600.0;
pub const SMOKE_HITS: u32 = 2;
pub const SMOKER_EPISODES: u32 = 2;
pub const HAIR_WINDOW: usize = 24;
pub const HAIR_FIRST: usize = 10;
pub const HAIR_FIRST_SHARE: f32 = 0.55;
pub const HAIR_CHANGE: usize = 16;
pub const HAIR_CHANGE_SHARE: f32 = 0.65;
pub const MAX_STATE: usize = 65_536;
pub const MIN_SAMPLES: u32 = 4;
pub const HAIR_COLORS: [&str; 12] = [
    "black", "brown", "grey", "white", "red", "orange", "yellow", "green", "cyan", "blue",
    "purple", "pink",
];
pub const KINDS: [&str; 6] = [
    "glasses",
    "beard",
    "fringe",
    "hair_color",
    "smoking",
    "smoker",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LookError {
    TooLarge,
    Format,
    Kind,
}

impl LookError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::TooLarge => "face.look.too_large",
            Self::Format => "face.look.format",
            Self::Kind => "face.look.kind",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct LookSample {
    pub glasses: f32,
    pub beard: f32,
    pub fringe: f32,
    pub cigarette: f32,
    pub hair: Option<String>,
    pub samples: u32,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LookEvent {
    pub kind: &'static str,
    pub value: String,
    pub previous: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct Flag {
    pub ema: f32,
    pub on: bool,
    pub streak: u32,
    pub seen: u32,
    pub since: f64,
}

impl Flag {
    fn update(&mut self, score: f32, now: f64) -> Option<bool> {
        if !score.is_finite() {
            return None;
        }
        let score = score.clamp(0.0, 1.0);
        self.seen = self.seen.saturating_add(1);
        self.ema = if self.seen == 1 {
            score
        } else {
            ALPHA.mul_add(score, (1.0 - ALPHA) * self.ema)
        };
        let target = if self.on {
            self.ema > OFF
        } else {
            self.ema >= ON
        };
        if target == self.on {
            self.streak = 0;
            return None;
        }
        self.streak = self.streak.saturating_add(1);
        if self.streak < STREAK || self.seen < MIN_SEEN {
            return None;
        }
        self.on = target;
        self.streak = 0;
        self.since = now;
        Some(target)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct Hair {
    pub recent: VecDeque<String>,
    pub stable: Option<String>,
    pub since: f64,
}

impl Hair {
    fn top(&self, last: usize) -> Option<(String, f32)> {
        let window: Vec<&String> = self.recent.iter().rev().take(last).collect();
        let total = window.len();
        HAIR_COLORS
            .iter()
            .map(|c| (*c, window.iter().filter(|w| w.as_str() == *c).count()))
            .max_by_key(|(_, n)| *n)
            .filter(|(_, n)| *n > 0)
            .map(|(c, n)| {
                #[allow(clippy::cast_precision_loss)]
                let share = n as f32 / total.max(1) as f32;
                (c.to_owned(), share)
            })
    }

    fn update(&mut self, color: &str, now: f64) -> Option<LookEvent> {
        let color = HAIR_COLORS.iter().find(|c| **c == color)?;
        self.recent.push_back((*color).to_owned());
        while self.recent.len() > HAIR_WINDOW {
            self.recent.pop_front();
        }
        let (need, share, last) = if self.stable.is_some() {
            (HAIR_CHANGE, HAIR_CHANGE_SHARE, HAIR_CHANGE)
        } else {
            (HAIR_FIRST, HAIR_FIRST_SHARE, HAIR_WINDOW)
        };
        if self.recent.len() < need {
            return None;
        }
        let (top, got) = self.top(last)?;
        if got < share || self.stable.as_deref() == Some(top.as_str()) {
            return None;
        }
        let previous = self.stable.replace(top.clone());
        self.since = now;
        Some(LookEvent {
            kind: "hair_color",
            value: top,
            previous,
        })
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct Smoke {
    pub episodes: u32,
    pub hits: u32,
    pub open: bool,
    pub last: f64,
    pub smoker: bool,
}

impl Smoke {
    fn update(&mut self, share: f32, now: f64, out: &mut Vec<LookEvent>) {
        if now - self.last > SMOKE_GAP_S {
            self.hits = 0;
            self.open = false;
        }
        if !share.is_finite() || share < SMOKE_HIT {
            return;
        }
        self.hits = self.hits.saturating_add(1);
        self.last = now;
        if self.open || self.hits < SMOKE_HITS {
            return;
        }
        self.open = true;
        self.episodes = self.episodes.saturating_add(1);
        out.push(LookEvent {
            kind: "smoking",
            value: "episode".to_owned(),
            previous: None,
        });
        if !self.smoker && self.episodes >= SMOKER_EPISODES {
            self.smoker = true;
            out.push(LookEvent {
                kind: "smoker",
                value: "on".to_owned(),
                previous: None,
            });
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
#[allow(clippy::struct_excessive_bools)]
pub struct LookSummary {
    pub glasses: bool,
    pub beard: bool,
    pub fringe: bool,
    pub hair: Option<String>,
    pub smoker: bool,
    pub smoking_episodes: u32,
    pub observations: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct LookMemory {
    pub version: u8,
    pub glasses: Flag,
    pub beard: Flag,
    pub fringe: Flag,
    pub hair: Hair,
    pub smoke: Smoke,
}

fn flag_event(kind: &'static str, change: Option<bool>) -> Option<LookEvent> {
    change.map(|on| LookEvent {
        kind,
        value: if on { "on" } else { "off" }.to_owned(),
        previous: Some(if on { "off" } else { "on" }.to_owned()),
    })
}

impl LookMemory {
    #[must_use]
    pub fn new() -> Self {
        Self {
            version: 1,
            ..Self::default()
        }
    }

    pub fn from_json(text: &str) -> Result<Self, LookError> {
        if text.len() > MAX_STATE {
            return Err(LookError::TooLarge);
        }
        if text.trim().is_empty() {
            return Ok(Self::new());
        }
        let mut memory: Self = serde_json::from_str(text).map_err(|_| LookError::Format)?;
        memory
            .hair
            .recent
            .retain(|c| HAIR_COLORS.contains(&c.as_str()));
        while memory.hair.recent.len() > HAIR_WINDOW {
            memory.hair.recent.pop_front();
        }
        if memory
            .hair
            .stable
            .as_deref()
            .is_some_and(|c| !HAIR_COLORS.contains(&c))
        {
            memory.hair.stable = None;
        }
        memory.version = 1;
        Ok(memory)
    }

    pub fn to_json(&self) -> Result<String, LookError> {
        serde_json::to_string(self).map_err(|_| LookError::Format)
    }

    pub fn update(&mut self, sample: &LookSample, now: f64) -> Vec<LookEvent> {
        let mut out = Vec::new();
        if sample.samples < MIN_SAMPLES || !now.is_finite() {
            return out;
        }
        out.extend(flag_event(
            "glasses",
            self.glasses.update(sample.glasses, now),
        ));
        out.extend(flag_event("beard", self.beard.update(sample.beard, now)));
        out.extend(flag_event("fringe", self.fringe.update(sample.fringe, now)));
        if let Some(color) = sample.hair.as_deref() {
            out.extend(self.hair.update(color, now));
        }
        self.smoke.update(sample.cigarette, now, &mut out);
        out
    }

    pub fn forget(&mut self, kind: &str) -> Result<(), LookError> {
        match kind {
            "glasses" => self.glasses = Flag::default(),
            "beard" => self.beard = Flag::default(),
            "fringe" => self.fringe = Flag::default(),
            "hair_color" => self.hair = Hair::default(),
            "smoking" | "smoker" => self.smoke = Smoke::default(),
            _ => return Err(LookError::Kind),
        }
        Ok(())
    }

    #[must_use]
    pub fn summary(&self) -> LookSummary {
        LookSummary {
            glasses: self.glasses.on,
            beard: self.beard.on,
            fringe: self.fringe.on,
            hair: self.hair.stable.clone(),
            smoker: self.smoke.smoker,
            smoking_episodes: self.smoke.episodes,
            observations: self.glasses.seen,
        }
    }
}
