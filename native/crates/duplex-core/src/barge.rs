use std::collections::HashSet;

use serde::{Deserialize, Serialize};

use crate::error::{DuplexError, DuplexResult};
use crate::session::{CutReport, Session};
use crate::state::State;

const CATALOG: &str = include_str!("backchannel.json");

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Known,
    Guest,
    Broadcast,
    Uncertain,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Risk {
    Low,
    High,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Evidence {
    pub verdict: Verdict,
    pub margin_permille: u16,
    pub voiced: bool,
    pub frame_ms: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BargeSettings {
    pub min_voiced_ms: u32,
    pub duck_after_ms: u32,
    pub duck_ms: u64,
    pub min_margin_permille: u16,
    pub guest_may_interrupt: bool,
    pub cooldown_ms: u64,
    pub pre_roll_ms: u32,
}

impl Default for BargeSettings {
    fn default() -> Self {
        Self {
            min_voiced_ms: 250,
            duck_after_ms: 100,
            duck_ms: 3_000,
            min_margin_permille: 600,
            guest_may_interrupt: true,
            cooldown_ms: 400,
            pre_roll_ms: 600,
        }
    }
}

impl BargeSettings {
    pub fn validate(&self) -> DuplexResult<()> {
        let ok = (100..=2_000).contains(&self.min_voiced_ms)
            && self.duck_after_ms <= self.min_voiced_ms
            && (500..=30_000).contains(&self.duck_ms)
            && (1..=1_000).contains(&self.min_margin_permille)
            && self.cooldown_ms <= 10_000
            && (100..=5_000).contains(&self.pre_roll_ms);
        if ok {
            Ok(())
        } else {
            Err(DuplexError::Settings)
        }
    }

    pub fn from_json(text: &str) -> DuplexResult<Self> {
        if text.len() > 4_096 {
            return Err(DuplexError::TooLarge);
        }
        let s: Self = serde_json::from_str(text).map_err(|_| DuplexError::Parse)?;
        s.validate()?;
        Ok(s)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Decision {
    Hold,
    Duck,
    Restore,
    Cut(CutReport),
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize)]
pub struct BargeStats {
    pub cuts: u32,
    pub ducks: u32,
    pub ignored_broadcast: u32,
    pub ignored_uncertain: u32,
    pub ignored_guest: u32,
    pub ignored_weak: u32,
}

#[derive(Debug)]
pub struct BargeDetector {
    settings: BargeSettings,
    voiced_ms: u32,
    ducked_at: Option<u64>,
    cooldown_until: u64,
    stats: BargeStats,
}

impl BargeDetector {
    pub fn new(settings: BargeSettings) -> DuplexResult<Self> {
        settings.validate()?;
        Ok(Self {
            settings,
            voiced_ms: 0,
            ducked_at: None,
            cooldown_until: 0,
            stats: BargeStats::default(),
        })
    }

    #[must_use]
    pub const fn stats(&self) -> &BargeStats {
        &self.stats
    }

    #[must_use]
    pub const fn pre_roll_ms(&self) -> u32 {
        self.settings.pre_roll_ms
    }

    fn eligible(&mut self, ev: Evidence) -> bool {
        match ev.verdict {
            Verdict::Broadcast => {
                self.stats.ignored_broadcast = self.stats.ignored_broadcast.saturating_add(1);
                false
            }
            Verdict::Uncertain => {
                self.stats.ignored_uncertain = self.stats.ignored_uncertain.saturating_add(1);
                false
            }
            Verdict::Guest if !self.settings.guest_may_interrupt => {
                self.stats.ignored_guest = self.stats.ignored_guest.saturating_add(1);
                false
            }
            Verdict::Known | Verdict::Guest => {
                if ev.margin_permille < self.settings.min_margin_permille {
                    self.stats.ignored_weak = self.stats.ignored_weak.saturating_add(1);
                    false
                } else {
                    true
                }
            }
        }
    }

    pub fn step(&mut self, session: &mut Session, ev: &Evidence, now_ms: u64) -> Decision {
        if session.state() != State::Speaking {
            self.voiced_ms = 0;
            self.ducked_at = None;
            return Decision::Hold;
        }
        if !ev.voiced || !self.eligible(*ev) {
            self.voiced_ms = 0;
            return self.restore_if_due(now_ms);
        }
        self.voiced_ms = self.voiced_ms.saturating_add(ev.frame_ms);
        if self.voiced_ms >= self.settings.min_voiced_ms && now_ms >= self.cooldown_until {
            return self.fire(session, now_ms);
        }
        if self.voiced_ms >= self.settings.duck_after_ms && self.ducked_at.is_none() {
            self.ducked_at = Some(now_ms);
            self.stats.ducks = self.stats.ducks.saturating_add(1);
            return Decision::Duck;
        }
        Decision::Hold
    }

    fn fire(&mut self, session: &mut Session, now_ms: u64) -> Decision {
        self.voiced_ms = 0;
        self.ducked_at = None;
        match session.cut(0, now_ms) {
            Ok(report) => {
                self.cooldown_until = now_ms.saturating_add(self.settings.cooldown_ms);
                self.stats.cuts = self.stats.cuts.saturating_add(1);
                Decision::Cut(report)
            }
            Err(_) => Decision::Hold,
        }
    }

    fn restore_if_due(&mut self, now_ms: u64) -> Decision {
        match self.ducked_at {
            Some(at) if now_ms.saturating_sub(at) >= self.settings.duck_ms => {
                self.ducked_at = None;
                Decision::Restore
            }
            _ => Decision::Hold,
        }
    }

    pub fn tick(&mut self, now_ms: u64) -> Decision {
        self.restore_if_due(now_ms)
    }
}

#[must_use]
pub const fn may_command(verdict: Verdict, risk: Risk) -> bool {
    match (verdict, risk) {
        (Verdict::Known, _) | (Verdict::Guest, Risk::Low) => true,
        (Verdict::Guest, Risk::High) | (Verdict::Broadcast | Verdict::Uncertain, _) => false,
    }
}

#[derive(Debug, Deserialize)]
struct CatalogFile {
    max_words: usize,
    fillers: Vec<String>,
}

#[derive(Debug)]
pub struct Backchannel {
    max_words: usize,
    fillers: HashSet<String>,
}

impl Backchannel {
    pub fn builtin() -> DuplexResult<Self> {
        Self::from_json(CATALOG)
    }

    pub fn from_json(text: &str) -> DuplexResult<Self> {
        if text.len() > 16_384 {
            return Err(DuplexError::TooLarge);
        }
        let file: CatalogFile = serde_json::from_str(text).map_err(|_| DuplexError::Parse)?;
        if file.max_words == 0
            || file.max_words > 6
            || file.fillers.is_empty()
            || file.fillers.len() > 256
        {
            return Err(DuplexError::Invalid);
        }
        Ok(Self {
            max_words: file.max_words,
            fillers: file.fillers.into_iter().map(|f| f.to_lowercase()).collect(),
        })
    }

    #[must_use]
    pub fn is_backchannel(&self, text: &str) -> bool {
        let words: Vec<String> = text
            .split_whitespace()
            .map(|w| {
                w.trim_matches(|c: char| !c.is_alphanumeric() && c != '\'')
                    .to_lowercase()
            })
            .filter(|w| !w.is_empty())
            .collect();
        !words.is_empty()
            && words.len() <= self.max_words
            && words.iter().all(|w| self.fillers.contains(w))
    }
}

#[derive(Debug)]
pub struct PreRoll {
    buffer: std::collections::VecDeque<u8>,
    capacity: usize,
}

impl PreRoll {
    pub fn new(rate_hz: u32, ms: u32, bytes_per_sample: u32) -> DuplexResult<Self> {
        if !(8_000..=96_000).contains(&rate_hz)
            || !(1..=4).contains(&bytes_per_sample)
            || !(100..=5_000).contains(&ms)
        {
            return Err(DuplexError::Settings);
        }
        let capacity = usize::try_from(
            u64::from(rate_hz)
                .saturating_mul(u64::from(ms))
                .saturating_mul(u64::from(bytes_per_sample))
                / 1_000,
        )
        .map_err(|_| DuplexError::Settings)?;
        Ok(Self {
            buffer: std::collections::VecDeque::with_capacity(capacity),
            capacity,
        })
    }

    pub fn push(&mut self, pcm: &[u8]) {
        let skip = pcm.len().saturating_sub(self.capacity);
        let tail = pcm.get(skip..).unwrap_or(&[]);
        let overflow = self
            .buffer
            .len()
            .saturating_add(tail.len())
            .saturating_sub(self.capacity);
        self.buffer.drain(..overflow.min(self.buffer.len()));
        self.buffer.extend(tail.iter().copied());
    }

    #[must_use]
    pub fn snapshot(&self) -> Vec<u8> {
        self.buffer.iter().copied().collect()
    }

    #[must_use]
    pub const fn capacity(&self) -> usize {
        self.capacity
    }

    pub fn clear(&mut self) {
        self.buffer.clear();
    }
}
